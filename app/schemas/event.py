from pydantic import BaseModel


class EventCreateReq(BaseModel):
    storeId: str
    title: str
    condition: str
    reward: int


class EventResp(BaseModel):
    id: str
    title: str
    condition: str
    reward: int
    isActive: bool


class EventListResp(BaseModel):
    events: list[EventResp]


class ApplicationSummary(BaseModel):
    id: str
    reviewerId: str
    reviewerName: str
    status: str
    appliedAt: str
    hasSubmission: bool


class EventApplicationsResp(BaseModel):
    applications: list[ApplicationSummary]
    totalCount: int
    currentPage: int
    totalPages: int
    hasNext: bool
