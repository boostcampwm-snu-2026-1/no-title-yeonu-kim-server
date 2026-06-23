from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.repository import ApplicationRepository
from app.application.repository_impl import ApplicationRepositoryImpl
from app.application.service import ApplicationService
from app.application.service_impl import ApplicationServiceImpl
from app.blockchain.dependencies import get_blockchain_service
from app.blockchain.service import BlockchainService
from app.db.session import get_db
from app.s3.dependencies import get_s3_service
from app.s3.service import S3Service


def get_application_repository(
    db: AsyncSession = Depends(get_db),
) -> ApplicationRepository:
    return ApplicationRepositoryImpl(db)


def get_application_service(
    repo: ApplicationRepository = Depends(get_application_repository),
    blockchain: BlockchainService = Depends(get_blockchain_service),
    s3: S3Service = Depends(get_s3_service),
) -> ApplicationService:
    return ApplicationServiceImpl(repo, blockchain, s3)
