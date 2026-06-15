from pydantic import BaseModel

from app.schemas.common import StoreType


class StoreCreateReq(BaseModel):
    name: str
    address: str
    category: StoreType
    thumbnailUrl: str | None = None
    description: str | None = None


class StoreResp(BaseModel):
    id: str
    name: str
    address: str
    category: StoreType
    thumbnailKey: str | None = None
    description: str | None = None


class StoreDetailResp(BaseModel):
    id: str
    name: str
    address: str


class StoreEventSummary(BaseModel):
    id: str
    title: str
    condition: str
    reward: int
    isActive: bool


class StoreListItem(BaseModel):
    id: str
    name: str
    address: str
    category: StoreType
    thumbnailKey: str | None = None
    description: str | None = None
    events: list[StoreEventSummary]
    totalEventCount: int


class StoreListResp(BaseModel):
    stores: list[StoreListItem]
    totalCount: int
    currentPage: int
    totalPages: int
    hasNext: bool


class StoreEventsResp(BaseModel):
    events: list[StoreEventSummary]
