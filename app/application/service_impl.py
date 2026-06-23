import asyncio
import base64
import logging
import re
from typing import Literal, cast
from uuid import UUID

import anthropic
import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from fastapi import BackgroundTasks

from app.application.models import Application
from app.application.repository import ApplicationRepository
from app.application.schemas import (
    ApplicationCreateReq,
    ApplicationItem,
    ReviewSubmissionDetail,
    ReviewSubmissionReq,
)
from app.application.service import ApplicationService
from app.blockchain.service import BlockchainService
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

logger = logging.getLogger(__name__)

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
    verdict = (
        block.text.strip()
        if isinstance(block, anthropic.types.TextBlock)
        else "(non-text block)"
    )
    logger.warning("[IMAGE_VALIDATION] key=%s verdict=%r", image_key, verdict)
    if not isinstance(block, anthropic.types.TextBlock) or "FAIL" in block.text.upper():
        raise ImageConditionNotMetError()


class ApplicationServiceImpl(ApplicationService):
    def __init__(
        self, repo: ApplicationRepository, blockchain: BlockchainService
    ) -> None:
        self.repo = repo
        self.blockchain = blockchain

    async def create_application(
        self,
        reviewer_id: str,
        data: ApplicationCreateReq,
        background_tasks: BackgroundTasks,
    ) -> None:
        if not _ETHEREUM_ADDRESS_RE.fullmatch(data.walletAddress):
            raise AppException(GEN_005)

        event = await self.repo.find_event_by_id(UUID(data.eventId))
        if not event:
            raise AppException(EVENT_001)

        if not event.is_active:
            raise AppException(GEN_003_CLOSED)

        existing = await self.repo.find_by_event_and_reviewer(
            UUID(data.eventId), UUID(reviewer_id)
        )
        if existing:
            raise AppException(APPLICATION_003_APPLY)

        await _validate_image_condition(data.imageKey, event.condition)

        application = Application(
            event_id=UUID(data.eventId),
            reviewer_id=UUID(reviewer_id),
            wallet_address=data.walletAddress,
            image_key=data.imageKey,
            status="APPROVED",
        )
        await self.repo.save_application(application)

        if event.contract_address:
            reviewer = await self.repo.find_user_by_id(UUID(reviewer_id))
            reviewer_email = reviewer.email if reviewer else ""
            background_tasks.add_task(
                self.blockchain.payout_safe,
                event.contract_address,
                data.walletAddress,
                event.reward,
                reviewer_email,
                event.title,
            )

    async def list_my_applications(
        self, reviewer_id: str, page: int, size: int
    ) -> tuple[list[ApplicationItem], int]:
        apps, total = await self.repo.find_by_reviewer_id(
            UUID(reviewer_id), offset=page * size, limit=size
        )

        result: list[ApplicationItem] = []
        for app in apps:
            submission = await self.repo.find_submission_by_application_id(app.id)
            submission_detail = None
            if submission:
                images = await self.repo.find_images_by_submission_id(submission.id)
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
        return result, total

    async def cancel_application(self, application_id: str, user_id: str) -> None:
        application = await self.repo.find_by_id(UUID(application_id))
        if not application:
            raise AppException(APPLICATION_002)
        if str(application.reviewer_id) != user_id:
            raise AppException(APPLICATION_001)
        if application.status != "PENDING":
            raise AppException(GEN_003_STATUS)
        await self.repo.delete(application)

    async def submit_review(
        self, application_id: str, user_id: str, data: ReviewSubmissionReq
    ) -> None:
        application = await self.repo.find_by_id(UUID(application_id))
        if not application:
            raise AppException(APPLICATION_002)
        if str(application.reviewer_id) != user_id:
            raise AppException(APPLICATION_001)
        existing = await self.repo.find_submission_by_application_id(
            UUID(application_id)
        )
        if existing:
            raise AppException(APPLICATION_003_SUBMIT)
        await self.repo.save_review(UUID(application_id), data.comment, data.imageList)
