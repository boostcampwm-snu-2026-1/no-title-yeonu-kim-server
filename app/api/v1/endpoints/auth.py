from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    AccessTokenResp,
    AuthResp,
    EmailCheckReq,
    EmailValidateReq,
    EmailValidateResp,
    EmailVerifyReq,
    LoginReq,
    RegisterReq,
    UserInfo,
)
from app.schemas.common import SuccessResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/email", response_model=SuccessResponse[None])
async def check_email(
    body: EmailCheckReq,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    await auth_service.check_email_duplicate(db, body.email)
    return SuccessResponse(data=None)


@router.post("/email/verify", response_model=SuccessResponse[None])
async def verify_email(
    body: EmailVerifyReq,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    await auth_service.send_verification_code(db, body.email)
    return SuccessResponse(data=None)


@router.post("/email/validate", response_model=SuccessResponse[EmailValidateResp])
async def validate_email(
    body: EmailValidateReq,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[EmailValidateResp]:
    token = await auth_service.validate_verification_code(db, body.email, body.code)
    return SuccessResponse(data=EmailValidateResp(verificationToken=token))


@router.post("/user", response_model=SuccessResponse[AuthResp])
async def register(
    body: RegisterReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AuthResp]:
    user, access_token, refresh_token = await auth_service.register(db, body)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
    )
    return SuccessResponse(
        data=AuthResp(
            user=UserInfo(id=str(user.id), userRole=user.role),
            token=access_token,
        )
    )


@router.get("/token", response_model=SuccessResponse[AccessTokenResp])
async def refresh_token(request: Request) -> SuccessResponse[AccessTokenResp]:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 없습니다.",
        )
    access_token = auth_service.refresh_access_token(token)
    return SuccessResponse(data=AccessTokenResp(accessToken=access_token))


@router.post("/user/session", response_model=SuccessResponse[AuthResp])
async def login(
    body: LoginReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AuthResp]:
    user, access_token, refresh_token = await auth_service.login(db, body)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
    )
    return SuccessResponse(
        data=AuthResp(
            user=UserInfo(id=str(user.id), userRole=user.role),
            token=access_token,
        )
    )
