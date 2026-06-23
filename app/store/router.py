from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import require_login
from app.schemas.common import StoreType
from app.store.dependencies import get_store_service
from app.store.schemas import (
    StoreCreateReq,
    StoreDetailResp,
    StoreEventsResp,
    StoreListResp,
    StoreResp,
)
from app.store.service import StoreService

router = APIRouter(prefix="/store", tags=["Store"])


@router.get("", response_model=StoreListResp)
async def list_stores(
    category: StoreType | None = Query(default=None),
    name: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    service: StoreService = Depends(get_store_service),
) -> StoreListResp:
    stores, total = await service.list_stores(
        category=category, name=name, page=page, size=size
    )
    total_pages = max(1, (total + size - 1) // size)
    return StoreListResp(
        stores=stores,
        totalCount=total,
        currentPage=page,
        totalPages=total_pages,
        hasNext=(page + 1) < total_pages,
    )


@router.post("", response_model=StoreResp)
async def create_store(
    body: StoreCreateReq,
    owner_id: str = Depends(require_login),
    service: StoreService = Depends(get_store_service),
) -> StoreResp:
    store = await service.create_store(owner_id, body)
    return StoreResp(
        id=str(store.id),
        name=store.name,
        address=store.address,
        category=store.category,
        thumbnailKey=store.thumbnail_key,
        description=store.description,
    )


@router.get("/{storeId}/events", response_model=StoreEventsResp)
async def get_store_events(
    storeId: str,
    service: StoreService = Depends(get_store_service),
) -> StoreEventsResp:
    events = await service.list_store_events(storeId)
    return StoreEventsResp(events=events)


@router.get("/{storeId}", response_model=StoreDetailResp)
async def get_store(
    storeId: str,
    service: StoreService = Depends(get_store_service),
) -> StoreDetailResp:
    store = await service.get_store(storeId)
    return StoreDetailResp(
        id=str(store.id),
        name=store.name,
        address=store.address,
    )


@router.delete("/{storeId}", response_model=None)
async def delete_store(
    storeId: str,
    user_id: str = Depends(require_login),
    service: StoreService = Depends(get_store_service),
) -> None:
    await service.delete_store(storeId, user_id)
