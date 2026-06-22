from fastapi import APIRouter, Depends, Request, Response

from app.api.v1.deps import require_login
from app.auth.dependencies import get_auth_service
from app.auth.schemas import (
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
from app.auth.service import AuthService
from app.core.exceptions import AUTH_001, AppException

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/email", response_model=None)
async def check_email(
    body: EmailCheckReq,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.check_email_duplicate(body.email)


@router.post("/email/verify", response_model=None)
async def verify_email(
    body: EmailVerifyReq,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.send_verification_code(body.email)


@router.post("/email/validate", response_model=EmailValidateResp)
async def validate_email(
    body: EmailValidateReq,
    service: AuthService = Depends(get_auth_service),
) -> EmailValidateResp:
    token = await service.validate_verification_code(body.email, body.code)
    return EmailValidateResp(verificationToken=token)


@router.post("/user", response_model=AuthResp)
async def register(
    body: RegisterReq,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResp:
    user, access_token, refresh_token = await service.register(body)
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
async def refresh_token(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AccessTokenResp:
    token = request.cookies.get("refresh_token")
    if not token:
        raise AppException(AUTH_001)
    access_token = service.refresh_access_token(token)
    return AccessTokenResp(accessToken=access_token)


@router.post("/user/session", response_model=AuthResp)
async def login(
    body: LoginReq,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResp:
    user, access_token, refresh_token = await service.login(body)
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
    service: AuthService = Depends(get_auth_service),
    user_id: str = Depends(require_login),
) -> None:
    await service.change_password(user_id, body.oldPassword, body.newPassword)


@router.post("/password", response_model=None)
async def reset_password(
    body: ResetPasswordReq,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.reset_password(body)
