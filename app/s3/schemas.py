from pydantic import BaseModel

from app.schemas.common import S3FileType


class S3PresignedUploadReq(BaseModel):
    fileName: str
    fileType: S3FileType
    contentType: str


class S3PresignedUploadResp(BaseModel):
    url: str
    s3Key: str
