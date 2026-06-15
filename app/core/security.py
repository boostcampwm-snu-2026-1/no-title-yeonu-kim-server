from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return bool(pwd_context.verify(plain, hashed))


def get_password_hash(password: str) -> str:
    return str(pwd_context.hash(password))


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(days=7),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def create_verification_token(email: str) -> str:
    payload = {
        "sub": email,
        "type": "email_verification",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def decode_token(token: str) -> str:
    payload: dict[str, object] = jwt.decode(
        token, settings.secret_key, algorithms=["HS256"]
    )
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise ValueError("Invalid token payload")
    return user_id
