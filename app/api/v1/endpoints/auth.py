from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
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
