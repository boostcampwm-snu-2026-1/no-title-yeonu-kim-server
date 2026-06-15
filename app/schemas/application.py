from pydantic import BaseModel


class ApplicationCreateReq(BaseModel):
    eventId: str
    walletAddress: str
    imageKey: str


class ReviewSubmissionReq(BaseModel):
    imageList: list[str]
    comment: str


class ReviewSubmissionDetail(BaseModel):
    id: str
    message: str
    reviewImages: list[str]


class ApplicationItem(BaseModel):
    id: str
    eventId: str
    status: str
    reviewSubmission: ReviewSubmissionDetail | None = None
    appliedAt: str


class ApplicationListResp(BaseModel):
    applications: list[ApplicationItem]
    totalCount: int
    currentPage: int
    totalPages: int
    hasNext: bool
