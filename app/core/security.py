from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


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
