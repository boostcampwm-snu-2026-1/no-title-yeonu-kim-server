from abc import ABC, abstractmethod

from app.s3.schemas import S3PresignedUploadResp
from app.schemas.common import S3FileType


class S3Service(ABC):
    @abstractmethod
    def generate_presigned_upload_url(
        self, file_name: str, file_type: S3FileType, content_type: str
    ) -> S3PresignedUploadResp: ...
