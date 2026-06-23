from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.store.repository import StoreRepository
from app.store.repository_impl import StoreRepositoryImpl
from app.store.service import StoreService
from app.store.service_impl import StoreServiceImpl


def get_store_repository(db: AsyncSession = Depends(get_db)) -> StoreRepository:
    return StoreRepositoryImpl(db)


def get_store_service(
    repo: StoreRepository = Depends(get_store_repository),
) -> StoreService:
    return StoreServiceImpl(repo)
