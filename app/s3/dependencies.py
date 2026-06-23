from app.s3.service import S3Service
from app.s3.service_impl import S3ServiceImpl


def get_s3_service() -> S3Service:
    return S3ServiceImpl()
