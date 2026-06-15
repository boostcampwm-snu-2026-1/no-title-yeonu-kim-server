from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: int = 200
    data: T


class ErrorDetail(BaseModel):
    timestamp: str
    message: str
    code: str


class ErrorResponse(BaseModel):
    status: int
    data: ErrorDetail


class UserRole(StrEnum):
    OWNER = "OWNER"
    REVIEWER = "REVIEWER"


class StoreType(StrEnum):
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    FASHION = "FASHION"
    BEAUTY = "BEAUTY"
    ETC = "ETC"


class ApplicationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class S3FileType(StrEnum):
    REVIEW = "REVIEW"
    STORE = "STORE"
