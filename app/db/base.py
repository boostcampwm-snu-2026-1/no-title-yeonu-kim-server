from sqlalchemy.orm import DeclarativeBase

from app.auth.models import EmailVerification, User  # noqa: F401


class Base(DeclarativeBase):
    pass
