from abc import ABC, abstractmethod

from fastapi import BackgroundTasks

from app.application.schemas import (
    ApplicationCreateReq,
    ApplicationItem,
    ReviewSubmissionReq,
)


class ApplicationService(ABC):
    @abstractmethod
    async def create_application(
        self,
        reviewer_id: str,
        data: ApplicationCreateReq,
        background_tasks: BackgroundTasks,
    ) -> None: ...

    @abstractmethod
    async def list_my_applications(
        self, reviewer_id: str, page: int, size: int
    ) -> tuple[list[ApplicationItem], int]: ...

    @abstractmethod
    async def cancel_application(self, application_id: str, user_id: str) -> None: ...

    @abstractmethod
    async def submit_review(
        self, application_id: str, user_id: str, data: ReviewSubmissionReq
    ) -> None: ...
