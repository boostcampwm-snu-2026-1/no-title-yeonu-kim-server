import asyncio
import base64
import re
from typing import Literal, cast
from uuid import UUID

import anthropic
import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    APPLICATION_001,
    APPLICATION_002,
    APPLICATION_003_APPLY,
    APPLICATION_003_SUBMIT,
    EVENT_001,
    GEN_003_CLOSED,
    GEN_003_STATUS,
    GEN_005,
    IMAGE_002,
    AppException,
    ImageConditionNotMetError,
)
from app.models.application import Application
from app.models.event import Event
from app.models.review_image import ReviewImage
from app.models.review_submission import ReviewSubmission
from app.schemas.application import (
    ApplicationCreateReq,
    ApplicationItem,
    ReviewSubmissionDetail,
    ReviewSubmissionReq,
)

_MediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
_SUPPORTED_MEDIA_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)
_ETHEREUM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _to_media_type(content_type: str) -> _MediaType:
    if content_type in _SUPPORTED_MEDIA_TYPES:
        return cast(_MediaType, content_type)
    return "image/jpeg"


async def _download_image(image_key: str) -> tuple[bytes, str]:
    def _sync() -> tuple[bytes, str]:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        try:
            resp = s3.get_object(Bucket=settings.s3_private_bucket, Key=image_key)
        except ClientError as e:
            raise AppException(IMAGE_002) from e
        return resp["Body"].read(), str(resp.get("ContentType", "image/jpeg"))

    return await asyncio.get_running_loop().run_in_executor(None, _sync)


async def _validate_image_condition(image_key: str, condition: str) -> None:
    image_bytes, content_type = await _download_image(image_key)
    media_type = _to_media_type(content_type)
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-opus-4-8",
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"이미지가 아래 조건을 충족하는지 판단하세요.\n"
                            f"조건: {condition}\n\n"
                            "충족하면 'PASS', 충족하지 않으면 'FAIL'로만 응답하세요."
                        ),
                    },
                ],
            }
        ],
    )

    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock) or "FAIL" in block.text.upper():
        raise ImageConditionNotMetError()


async def create_application(
    db: AsyncSession, reviewer_id: str, data: ApplicationCreateReq
) -> None:
    if not _ETHEREUM_ADDRESS_RE.fullmatch(data.walletAddress):
        raise AppException(GEN_005)

    event = await db.scalar(select(Event).where(Event.id == UUID(data.eventId)))
    if not event:
        raise AppException(EVENT_001)

    if not event.is_active:
        raise AppException(GEN_003_CLOSED)

    existing = await db.scalar(
        select(Application).where(
            Application.event_id == UUID(data.eventId),
            Application.reviewer_id == UUID(reviewer_id),
        )
    )
    if existing:
        raise AppException(APPLICATION_003_APPLY)

    await _validate_image_condition(data.imageKey, event.condition)

    application = Application(
        event_id=UUID(data.eventId),
        reviewer_id=UUID(reviewer_id),
        wallet_address=data.walletAddress,
        image_key=data.imageKey,
    )
    db.add(application)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise AppException(APPLICATION_003_APPLY) from e


async def list_my_applications(
    db: AsyncSession, reviewer_id: str, page: int, size: int
) -> tuple[list[ApplicationItem], int]:
    base_query = select(Application).where(Application.reviewer_id == UUID(reviewer_id))
    _total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    total = _total if _total is not None else 0

    apps = (await db.scalars(base_query.offset((page - 1) * size).limit(size))).all()

    result: list[ApplicationItem] = []
    for app in apps:
        submission = await db.scalar(
            select(ReviewSubmission).where(ReviewSubmission.application_id == app.id)
        )
        submission_detail = None
        if submission:
            images = (
                await db.scalars(
                    select(ReviewImage)
                    .where(ReviewImage.submission_id == submission.id)
                    .order_by(ReviewImage.order)
                )
            ).all()
            submission_detail = ReviewSubmissionDetail(
                id=str(submission.id),
                message=submission.message,
                reviewImages=[img.image_key for img in images],
            )
        result.append(
            ApplicationItem(
                id=str(app.id),
                eventId=str(app.event_id),
                status=app.status,
                reviewSubmission=submission_detail,
                appliedAt=app.applied_at.isoformat(),
            )
        )
    return result, int(total)


async def cancel_application(
    db: AsyncSession, application_id: str, user_id: str
) -> None:
    application = await db.scalar(
        select(Application).where(Application.id == UUID(application_id))
    )
    if not application:
        raise AppException(APPLICATION_002)
    if str(application.reviewer_id) != user_id:
        raise AppException(APPLICATION_001)
    if application.status != "PENDING":
        raise AppException(GEN_003_STATUS)
    await db.delete(application)
    await db.commit()


async def submit_review(
    db: AsyncSession, application_id: str, user_id: str, data: ReviewSubmissionReq
) -> None:
    application = await db.scalar(
        select(Application).where(Application.id == UUID(application_id))
    )
    if not application:
        raise AppException(APPLICATION_002)
    if str(application.reviewer_id) != user_id:
        raise AppException(APPLICATION_001)
    existing = await db.scalar(
        select(ReviewSubmission).where(
            ReviewSubmission.application_id == UUID(application_id)
        )
    )
    if existing:
        raise AppException(APPLICATION_003_SUBMIT)

    submission = ReviewSubmission(
        application_id=UUID(application_id),
        message=data.comment,
    )
    db.add(submission)
    await db.flush()

    for i, image_key in enumerate(data.imageList):
        db.add(ReviewImage(submission_id=submission.id, image_key=image_key, order=i))

    await db.commit()
