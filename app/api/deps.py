from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db as _get_db

# Re-export for use in endpoint dependencies
get_db = _get_db

__all__ = ["get_db", "AsyncGenerator", "AsyncSession"]
