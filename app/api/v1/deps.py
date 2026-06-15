from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError

from app.core.exceptions import AUTH_001, AppException
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def require_login(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise AppException(AUTH_001)
    try:
        return decode_token(credentials.credentials)
    except (ExpiredSignatureError, DecodeError, ValueError) as e:
        raise AppException(AUTH_001) from e
