from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.email_verification import EmailVerification as _EV  # noqa: E402, F401
from app.models.user import User as _User  # noqa: E402, F401
