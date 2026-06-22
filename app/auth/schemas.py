from pydantic import BaseModel

from app.schemas.common import UserRole


class EmailCheckReq(BaseModel):
    email: str


class EmailVerifyReq(BaseModel):
    email: str


class EmailValidateReq(BaseModel):
    email: str
    code: str


class EmailValidateResp(BaseModel):
    verificationToken: str


class UserInfo(BaseModel):
    id: str
    userRole: str


class RegisterReq(BaseModel):
    role: UserRole
    username: str
    email: str
    password: str


class AuthResp(BaseModel):
    user: UserInfo
    token: str


class LoginReq(BaseModel):
    role: UserRole
    mail: str
    password: str


class AccessTokenResp(BaseModel):
    accessToken: str


class ChangePasswordReq(BaseModel):
    oldPassword: str
    newPassword: str


class ResetPasswordReq(BaseModel):
    email: str
