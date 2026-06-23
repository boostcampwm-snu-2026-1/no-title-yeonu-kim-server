from uuid import UUID

from app.blockchain.service import BlockchainService
from app.core.exceptions import AUTH_007, EVENT_001, STORE_001, AppException
from app.event.models import Event
from app.event.repository import EventRepository
from app.event.schemas import ApplicationSummary, EventCreateReq
from app.event.service import EventService


class EventServiceImpl(EventService):
    def __init__(self, repo: EventRepository, blockchain: BlockchainService) -> None:
        self.repo = repo
        self.blockchain = blockchain

    async def get_event(self, event_id: str) -> Event:
        event = await self.repo.find_by_id(UUID(event_id))
        if not event:
            raise AppException(EVENT_001)
        return event

    async def list_owner_events(self, owner_id: str) -> list[Event]:
        return await self.repo.find_by_owner_id(UUID(owner_id))

    async def create_event(self, owner_id: str, data: EventCreateReq) -> Event:
        store = await self.repo.find_store_by_id(UUID(data.storeId))
        if not store:
            raise AppException(STORE_001)
        if str(store.owner_id) != owner_id:
            raise AppException(AUTH_007)

        contract_address = await self.blockchain.deploy_contract()

        event = Event(
            store_id=UUID(data.storeId),
            title=data.title,
            condition=data.condition,
            reward=int(data.reward * 10**18),
            contract_address=contract_address,
        )
        return await self.repo.save(event)

    async def delete_event(self, event_id: str, owner_id: str) -> None:
        event = await self.get_event(event_id)
        store = await self.repo.find_store_by_id(event.store_id)
        if not store or str(store.owner_id) != owner_id:
            raise AppException(AUTH_007)
        await self.repo.delete(event)

    async def list_event_applications(
        self,
        event_id: str,
        owner_id: str,
        *,
        status_filter: str | None,
        page: int,
        size: int,
    ) -> tuple[list[ApplicationSummary], int]:
        event = await self.get_event(event_id)
        store = await self.repo.find_store_by_id(event.store_id)
        if not store or str(store.owner_id) != owner_id:
            raise AppException(AUTH_007)

        apps, total = await self.repo.find_applications_by_event_id(
            UUID(event_id),
            status_filter=status_filter,
            offset=page * size,
            limit=size,
        )

        result: list[ApplicationSummary] = []
        for app in apps:
            reviewer = await self.repo.find_user_by_id(app.reviewer_id)
            has_submission = bool(
                await self.repo.find_submission_by_application_id(app.id)
            )
            result.append(
                ApplicationSummary(
                    id=str(app.id),
                    reviewerId=str(app.reviewer_id),
                    reviewerName=reviewer.username if reviewer else "",
                    status=app.status,
                    appliedAt=app.applied_at.isoformat(),
                    hasSubmission=has_submission,
                )
            )

        return result, int(total)
