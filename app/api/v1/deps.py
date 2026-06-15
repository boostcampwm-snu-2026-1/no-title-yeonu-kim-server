from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError

from app.core.security import decode_token

bearer = HTTPBearer()


async def require_login(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    try:
        return decode_token(credentials.credentials)
    except (ExpiredSignatureError, DecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e
