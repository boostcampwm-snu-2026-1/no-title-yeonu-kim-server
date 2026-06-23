import uuid

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.exceptions import S3_001, AppException
from app.s3.schemas import S3PresignedUploadResp
from app.s3.service import S3Service
from app.schemas.common import S3FileType


class S3ServiceImpl(S3Service):
    def generate_presigned_upload_url(
        self, file_name: str, file_type: S3FileType, content_type: str
    ) -> S3PresignedUploadResp:
        bucket = (
            settings.s3_public_bucket
            if file_type == S3FileType.STORE
            else settings.s3_private_bucket
        )
        s3_key = f"{file_type.value.lower()}/{uuid.uuid4()}/{file_name}"

        client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
        )
        try:
            url: str = client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": s3_key, "ContentType": content_type},
                ExpiresIn=settings.s3_presigned_expiry,
            )
        except ClientError as e:
            raise AppException(S3_001) from e

        return S3PresignedUploadResp(url=url, s3Key=s3_key)
