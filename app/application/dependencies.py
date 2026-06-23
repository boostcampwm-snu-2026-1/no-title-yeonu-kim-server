from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.repository import ApplicationRepository
from app.application.repository_impl import ApplicationRepositoryImpl
from app.application.service import ApplicationService
from app.application.service_impl import ApplicationServiceImpl
from app.blockchain.dependencies import get_blockchain_service
from app.blockchain.service import BlockchainService
from app.db.session import get_db


def get_application_repository(
    db: AsyncSession = Depends(get_db),
) -> ApplicationRepository:
    return ApplicationRepositoryImpl(db)


def get_application_service(
    repo: ApplicationRepository = Depends(get_application_repository),
    blockchain: BlockchainService = Depends(get_blockchain_service),
) -> ApplicationService:
    return ApplicationServiceImpl(repo, blockchain)
