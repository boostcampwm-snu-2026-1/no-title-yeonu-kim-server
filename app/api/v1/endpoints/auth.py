from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_login
from app.core.exceptions import AUTH_001, AppException
from app.db.session import get_db
from app.schemas.auth import (
    AccessTokenResp,
    AuthResp,
    ChangePasswordReq,
    EmailCheckReq,
    EmailValidateReq,
    EmailValidateResp,
    EmailVerifyReq,
    LoginReq,
    RegisterReq,
    ResetPasswordReq,
    UserInfo,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/email", response_model=None)
async def check_email(
    body: EmailCheckReq,
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.check_email_duplicate(db, body.email)


@router.post("/email/verify", response_model=None)
async def verify_email(
    body: EmailVerifyReq,
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.send_verification_code(db, body.email)


@router.post("/email/validate", response_model=EmailValidateResp)
async def validate_email(
    body: EmailValidateReq,
    db: AsyncSession = Depends(get_db),
) -> EmailValidateResp:
    token = await auth_service.validate_verification_code(db, body.email, body.code)
    return EmailValidateResp(verificationToken=token)


@router.post("/user", response_model=AuthResp)
async def register(
    body: RegisterReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResp:
    user, access_token, refresh_token = await auth_service.register(db, body)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
    )
    return AuthResp(
        user=UserInfo(id=str(user.id), userRole=user.role),
        token=access_token,
    )


@router.get("/token", response_model=AccessTokenResp)
async def refresh_token(request: Request) -> AccessTokenResp:
    token = request.cookies.get("refresh_token")
    if not token:
        raise AppException(AUTH_001)
    access_token = auth_service.refresh_access_token(token)
    return AccessTokenResp(accessToken=access_token)


@router.post("/user/session", response_model=AuthResp)
async def login(
    body: LoginReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResp:
    user, access_token, refresh_token = await auth_service.login(db, body)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
    )
    return AuthResp(
        user=UserInfo(id=str(user.id), userRole=user.role),
        token=access_token,
    )


@router.delete("/user/session", response_model=None)
async def logout(
    response: Response,
    _user_id: str = Depends(require_login),
) -> None:
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")


@router.patch("/password", response_model=None)
async def change_password(
    body: ChangePasswordReq,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_login),
) -> None:
    await auth_service.change_password(db, user_id, body.oldPassword, body.newPassword)


@router.post("/password", response_model=None)
async def reset_password(
    body: ResetPasswordReq,
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.reset_password(db, body)
