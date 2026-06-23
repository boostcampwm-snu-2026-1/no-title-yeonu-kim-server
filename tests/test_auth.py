import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerification, User
from app.core.security import create_refresh_token, verify_password
from tests.conftest import auth_headers, create_user, create_verification


@pytest.mark.asyncio
class TestCheckEmail:
    async def test_available_email_returns_200(self, client: AsyncClient) -> None:
        res = await client.post("/api/auth/email", json={"email": "new@example.com"})
        assert res.status_code == 200
        assert res.json() is None

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="taken@example.com")
        res = await client.post("/api/auth/email", json={"email": "taken@example.com"})
        assert res.status_code == 409
        assert res.json()["status"] == 409


@pytest.mark.asyncio
class TestEmailVerify:
    async def test_creates_verification_record(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        res = await client.post(
            "/api/auth/email/verify", json={"email": "user@example.com"}
        )
        assert res.status_code == 200

        record = await db.scalar(
            select(EmailVerification).where(
                EmailVerification.email == "user@example.com"
            )
        )
        assert record is not None
        assert len(record.code) == 6
        assert record.code.isdigit()
        assert record.is_verified is False

    async def test_response_format(self, client: AsyncClient) -> None:
        res = await client.post(
            "/api/auth/email/verify", json={"email": "user@example.com"}
        )
        assert res.json() is None


@pytest.mark.asyncio
class TestEmailValidate:
    async def test_valid_code_returns_token(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_verification(db, email="user@example.com", code="111111")
        res = await client.post(
            "/api/auth/email/validate",
            json={"email": "user@example.com", "code": "111111"},
        )
        assert res.status_code == 200
        body = res.json()
        assert "verificationToken" in body
        assert isinstance(body["verificationToken"], str)

    async def test_valid_code_marks_verified_in_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        record = await create_verification(db, email="user@example.com", code="222222")
        await client.post(
            "/api/auth/email/validate",
            json={"email": "user@example.com", "code": "222222"},
        )
        await db.refresh(record)
        assert record.is_verified is True
        assert record.verification_token is not None

    async def test_wrong_code_returns_400(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_verification(db, email="user@example.com", code="333333")
        res = await client.post(
            "/api/auth/email/validate",
            json={"email": "user@example.com", "code": "000000"},
        )
        assert res.status_code == 400

    async def test_expired_code_returns_400(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_verification(
            db, email="user@example.com", code="444444", expired=True
        )
        res = await client.post(
            "/api/auth/email/validate",
            json={"email": "user@example.com", "code": "444444"},
        )
        assert res.status_code == 400

    async def test_already_verified_code_returns_400(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_verification(
            db, email="user@example.com", code="555555", is_verified=True
        )
        res = await client.post(
            "/api/auth/email/validate",
            json={"email": "user@example.com", "code": "555555"},
        )
        assert res.status_code == 400


_REGISTER_BODY = {
    "role": "REVIEWER",
    "username": "Alice",
    "email": "alice@example.com",
    "password": "secret123",
}


@pytest.mark.asyncio
class TestRegister:
    async def test_creates_user_in_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        res = await client.post("/api/auth/user", json=_REGISTER_BODY)
        assert res.status_code == 200

        user = await db.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        assert user.username == "Alice"
        assert user.role == "REVIEWER"

    async def test_password_is_hashed_in_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await client.post("/api/auth/user", json=_REGISTER_BODY)

        user = await db.scalar(select(User).where(User.email == "alice@example.com"))
        assert user is not None
        assert user.password_hash != "secret123"
        assert verify_password("secret123", user.password_hash)

    async def test_returns_access_token_and_user(self, client: AsyncClient) -> None:
        res = await client.post("/api/auth/user", json=_REGISTER_BODY)
        body = res.json()
        assert "token" in body
        assert body["user"]["userRole"] == "REVIEWER"

    async def test_sets_refresh_token_cookie(self, client: AsyncClient) -> None:
        res = await client.post("/api/auth/user", json=_REGISTER_BODY)
        assert "refresh_token" in res.cookies

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="alice@example.com")
        res = await client.post("/api/auth/user", json=_REGISTER_BODY)
        assert res.status_code == 409


@pytest.mark.asyncio
class TestLogin:
    async def test_valid_credentials_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="bob@example.com", password="pass", role="OWNER")
        res = await client.post(
            "/api/auth/user/session",
            json={"role": "OWNER", "mail": "bob@example.com", "password": "pass"},
        )
        assert res.status_code == 200
        body = res.json()
        assert "token" in body
        assert body["user"]["userRole"] == "OWNER"

    async def test_sets_refresh_token_cookie(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="bob@example.com", password="pass", role="OWNER")
        res = await client.post(
            "/api/auth/user/session",
            json={"role": "OWNER", "mail": "bob@example.com", "password": "pass"},
        )
        assert "refresh_token" in res.cookies

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="bob@example.com", password="pass")
        res = await client.post(
            "/api/auth/user/session",
            json={"role": "REVIEWER", "mail": "bob@example.com", "password": "wrong"},
        )
        assert res.status_code == 401

    async def test_role_mismatch_returns_401(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await create_user(db, email="bob@example.com", password="pass", role="OWNER")
        res = await client.post(
            "/api/auth/user/session",
            json={"role": "REVIEWER", "mail": "bob@example.com", "password": "pass"},
        )
        assert res.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(
            "/api/auth/user/session",
            json={"role": "REVIEWER", "mail": "nobody@example.com", "password": "x"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
class TestRefreshToken:
    async def test_valid_cookie_returns_access_token(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        token = create_refresh_token(str(user.id))
        client.cookies.set("refresh_token", token)
        res = await client.get("/api/auth/token")
        assert res.status_code == 200
        body = res.json()
        assert "accessToken" in body
        assert isinstance(body["accessToken"], str)

    async def test_no_cookie_returns_401(self, client: AsyncClient) -> None:
        res = await client.get("/api/auth/token")
        assert res.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        client.cookies.set("refresh_token", "this.is.invalid")
        res = await client.get("/api/auth/token")
        assert res.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    async def test_clears_refresh_cookie(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db)
        client.cookies.set("refresh_token", "some_token")
        res = await client.delete(
            "/api/auth/user/session", headers=auth_headers(user.id)
        )
        assert res.status_code == 200
        assert res.cookies.get("refresh_token") in ("", None)

    async def test_without_auth_returns_4xx(self, client: AsyncClient) -> None:
        res = await client.delete("/api/auth/user/session")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestChangePassword:
    async def test_changes_password_in_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, password="old_pass")
        res = await client.patch(
            "/api/auth/password",
            json={"oldPassword": "old_pass", "newPassword": "new_pass"},
            headers=auth_headers(user.id),
        )
        assert res.status_code == 200

        await db.refresh(user)
        assert not verify_password("old_pass", user.password_hash)
        assert verify_password("new_pass", user.password_hash)

    async def test_wrong_old_password_returns_401(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, password="correct")
        res = await client.patch(
            "/api/auth/password",
            json={"oldPassword": "wrong", "newPassword": "new_pass"},
            headers=auth_headers(user.id),
        )
        assert res.status_code == 401

    async def test_without_auth_returns_4xx(self, client: AsyncClient) -> None:
        res = await client.patch(
            "/api/auth/password",
            json={"oldPassword": "x", "newPassword": "y"},
        )
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestResetPassword:
    async def test_updates_password_hash_in_db(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await create_user(db, email="reset@example.com", password="original")
        original_hash = user.password_hash

        res = await client.post(
            "/api/auth/password", json={"email": "reset@example.com"}
        )
        assert res.status_code == 200

        await db.refresh(user)
        assert user.password_hash != original_hash
        assert not verify_password("original", user.password_hash)

    async def test_response_format(self, client: AsyncClient, db: AsyncSession) -> None:
        await create_user(db, email="reset@example.com")
        res = await client.post(
            "/api/auth/password", json={"email": "reset@example.com"}
        )
        assert res.json() is None

    async def test_unknown_email_returns_404(self, client: AsyncClient) -> None:
        res = await client.post(
            "/api/auth/password", json={"email": "ghost@example.com"}
        )
        assert res.status_code == 404
