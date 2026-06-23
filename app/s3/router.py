from fastapi import APIRouter, Depends

from app.s3.dependencies import get_s3_service
from app.s3.schemas import S3PresignedUploadReq, S3PresignedUploadResp
from app.s3.service import S3Service
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/s3", tags=["S3"])


@router.post("", response_model=SuccessResponse[S3PresignedUploadResp])
def create_presigned_upload_url(
    body: S3PresignedUploadReq,
    service: S3Service = Depends(get_s3_service),
) -> SuccessResponse[S3PresignedUploadResp]:
    result = service.generate_presigned_upload_url(
        body.fileName, body.fileType, body.contentType
    )
    return SuccessResponse(data=result)
