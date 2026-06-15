from fastapi import APIRouter

from app.schemas.s3 import S3PresignedUploadReq, S3PresignedUploadResp
from app.services import s3 as s3_service

router = APIRouter(prefix="/s3", tags=["S3"])


@router.post("", response_model=S3PresignedUploadResp)
def create_presigned_upload_url(body: S3PresignedUploadReq) -> S3PresignedUploadResp:
    return s3_service.generate_presigned_upload_url(
        body.fileName, body.fileType, body.contentType
    )
