import uuid

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.common import S3FileType
from app.schemas.s3 import S3PresignedUploadResp


def _get_s3_client() -> boto3.client:
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
    )


def generate_presigned_upload_url(
    file_name: str, file_type: S3FileType, content_type: str
) -> S3PresignedUploadResp:
    if file_type == S3FileType.STORE:
        bucket = settings.s3_public_bucket
    else:
        bucket = settings.s3_private_bucket
    s3_key = f"{file_type.value.lower()}/{uuid.uuid4()}/{file_name}"

    client = _get_s3_client()
    try:
        url: str = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": s3_key, "ContentType": content_type},
            ExpiresIn=settings.s3_presigned_expiry,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {e}",
        ) from e

    return S3PresignedUploadResp(url=url, s3Key=s3_key)
