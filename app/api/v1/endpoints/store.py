from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.db.session import get_db
from app.schemas.common import StoreType, SuccessResponse
from app.schemas.store import (
    StoreCreateReq,
    StoreDetailResp,
    StoreEventsResp,
    StoreListResp,
    StoreResp,
)
from app.services import store as store_service

router = APIRouter(prefix="/store", tags=["Store"])


@router.get("", response_model=SuccessResponse[StoreListResp])
async def list_stores(
    category: StoreType | None = Query(default=None),
    name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StoreListResp]:
    stores, total = await store_service.list_stores(
        db, category=category, name=name, page=page, size=size
    )
    total_pages = max(1, (total + size - 1) // size)
    return SuccessResponse(
        data=StoreListResp(
            stores=stores,
            totalCount=total,
            currentPage=page,
            totalPages=total_pages,
            hasNext=page < total_pages,
        )
    )


@router.post("", response_model=SuccessResponse[StoreResp])
async def create_store(
    body: StoreCreateReq,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(require_login),
) -> SuccessResponse[StoreResp]:
    store = await store_service.create_store(db, owner_id, body)
    return SuccessResponse(
        data=StoreResp(
            id=str(store.id),
            name=store.name,
            address=store.address,
            category=store.category,
            thumbnailKey=store.thumbnail_key,
            description=store.description,
        )
    )


@router.get("/{storeId}/events", response_model=SuccessResponse[StoreEventsResp])
async def get_store_events(
    storeId: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StoreEventsResp]:
    events = await store_service.list_store_events(db, storeId)
    return SuccessResponse(data=StoreEventsResp(events=events))


@router.get("/{storeId}", response_model=SuccessResponse[StoreDetailResp])
async def get_store(
    storeId: str,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StoreDetailResp]:
    store = await store_service.get_store_or_404(db, storeId)
    return SuccessResponse(
        data=StoreDetailResp(
            id=str(store.id),
            name=store.name,
            address=store.address,
        )
    )


@router.delete("/{storeId}", response_model=SuccessResponse[None])
async def delete_store(
    storeId: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_login),
) -> SuccessResponse[None]:
    await store_service.delete_store(db, storeId, user_id)
    return SuccessResponse(data=None)
