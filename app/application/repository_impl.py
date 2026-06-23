from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.models import Application, ReviewImage, ReviewSubmission
from app.application.repository import ApplicationRepository
from app.auth.models import User
from app.core.exceptions import APPLICATION_003_APPLY, AppException
from app.event.models import Event


class ApplicationRepositoryImpl(ApplicationRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_event_by_id(self, event_id: UUID) -> Event | None:
        return cast(
            Event | None,
            await self.db.scalar(select(Event).where(Event.id == event_id)),
        )

    async def find_by_id(self, application_id: UUID) -> Application | None:
        return cast(
            Application | None,
            await self.db.scalar(
                select(Application).where(Application.id == application_id)
            ),
        )

    async def find_by_event_and_reviewer(
        self, event_id: UUID, reviewer_id: UUID
    ) -> Application | None:
        return cast(
            Application | None,
            await self.db.scalar(
                select(Application).where(
                    Application.event_id == event_id,
                    Application.reviewer_id == reviewer_id,
                )
            ),
        )

    async def find_by_reviewer_id(
        self, reviewer_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[Application], int]:
        q = select(Application).where(Application.reviewer_id == reviewer_id)
        total = (
            await self.db.scalar(select(func.count()).select_from(q.subquery())) or 0
        )
        apps = list((await self.db.scalars(q.offset(offset).limit(limit))).all())
        return apps, int(total)

    async def find_user_by_id(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(select(User).where(User.id == user_id)),
        )

    async def find_submission_by_application_id(
        self, application_id: UUID
    ) -> ReviewSubmission | None:
        return cast(
            ReviewSubmission | None,
            await self.db.scalar(
                select(ReviewSubmission).where(
                    ReviewSubmission.application_id == application_id
                )
            ),
        )

    async def find_images_by_submission_id(
        self, submission_id: UUID
    ) -> list[ReviewImage]:
        return list(
            (
                await self.db.scalars(
                    select(ReviewImage)
                    .where(ReviewImage.submission_id == submission_id)
                    .order_by(ReviewImage.order)
                )
            ).all()
        )

    async def save_application(self, application: Application) -> None:
        self.db.add(application)
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise AppException(APPLICATION_003_APPLY) from e

    async def delete(self, application: Application) -> None:
        await self.db.delete(application)
        await self.db.commit()

    async def save_review(
        self, application_id: UUID, message: str, image_keys: list[str]
    ) -> None:
        submission = ReviewSubmission(
            application_id=application_id,
            message=message,
        )
        self.db.add(submission)
        await self.db.flush()
        for i, key in enumerate(image_keys):
            self.db.add(
                ReviewImage(submission_id=submission.id, image_key=key, order=i)
            )
        await self.db.commit()
