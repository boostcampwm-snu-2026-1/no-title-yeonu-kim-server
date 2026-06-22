"""Unit tests for app/auth/service_impl.py — repos and email sender are mocked."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.auth.schemas import LoginReq, RegisterReq, ResetPasswordReq
from app.auth.service_impl import AuthServiceImpl
from app.core.exceptions import (
    AUTH_001,
    AUTH_002,
    USER_001,
    USER_002,
    USER_006,
    AppException,
)
from app.core.security import decode_token, get_password_hash, verify_password


def _make_service() -> tuple[AuthServiceImpl, AsyncMock, AsyncMock, AsyncMock]:
    user_repo = AsyncMock()
    ev_repo = AsyncMock()
    email_sender = AsyncMock()
    svc = AuthServiceImpl(user_repo, ev_repo, email_sender)
    return svc, user_repo, ev_repo, email_sender


def _mock_user(
    *,
    email: str = "test@example.com",
    role: str = "REVIEWER",
    password: str = "pass",
) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.email = email
    user.role = role
    user.password_hash = get_password_hash(password)
    return user


@pytest.mark.asyncio
class TestCheckEmailDuplicate:
    async def test_raises_user_001_when_email_already_registered(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = _mock_user()
        with pytest.raises(AppException) as exc:
            await service.check_email_duplicate("taken@example.com")
        assert exc.value.code == USER_001.code
        assert exc.value.status_code == 409

    async def test_passes_silently_when_email_available(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        await service.check_email_duplicate("free@example.com")


@pytest.mark.asyncio
class TestSendVerificationCode:
    async def test_saves_verification_record(self) -> None:
        service, _, ev_repo, _ = _make_service()
        await service.send_verification_code("user@example.com")
        ev_repo.save.assert_awaited_once()

    async def test_generated_code_is_6_digits(self) -> None:
        service, _, ev_repo, _ = _make_service()
        await service.send_verification_code("user@example.com")
        record = ev_repo.save.call_args[0][0]
        assert len(record.code) == 6
        assert record.code.isdigit()

    async def test_sends_email_to_correct_recipient(self) -> None:
        service, _, _, email_sender = _make_service()
        await service.send_verification_code("target@example.com")
        email_sender.send.assert_awaited_once()
        to_addr = email_sender.send.call_args[0][0]
        assert to_addr == "target@example.com"

    async def test_verification_record_is_not_yet_verified(self) -> None:
        service, _, ev_repo, _ = _make_service()
        await service.send_verification_code("user@example.com")
        record = ev_repo.save.call_args[0][0]
        # SQLAlchemy evaluates default=False at INSERT time; value is None or False
        assert not record.is_verified


@pytest.mark.asyncio
class TestValidateVerificationCode:
    async def test_raises_user_006_when_no_matching_record(self) -> None:
        service, _, ev_repo, _ = _make_service()
        ev_repo.find_latest_unverified.return_value = None
        with pytest.raises(AppException) as exc:
            await service.validate_verification_code("u@example.com", "000000")
        assert exc.value.code == USER_006.code

    async def test_returns_verification_token_string_on_success(self) -> None:
        service, _, ev_repo, _ = _make_service()
        record = MagicMock()
        ev_repo.find_latest_unverified.return_value = record
        token = await service.validate_verification_code("u@example.com", "123456")
        assert isinstance(token, str) and len(token) > 10

    async def test_marks_record_as_verified(self) -> None:
        service, _, ev_repo, _ = _make_service()
        record = MagicMock()
        ev_repo.find_latest_unverified.return_value = record
        await service.validate_verification_code("u@example.com", "123456")
        assert record.is_verified is True

    async def test_sets_verification_token_on_record(self) -> None:
        service, _, ev_repo, _ = _make_service()
        record = MagicMock()
        record.verification_token = None
        ev_repo.find_latest_unverified.return_value = record
        await service.validate_verification_code("u@example.com", "123456")
        assert record.verification_token is not None

    async def test_calls_ev_repo_update_with_record(self) -> None:
        service, _, ev_repo, _ = _make_service()
        record = MagicMock()
        ev_repo.find_latest_unverified.return_value = record
        await service.validate_verification_code("u@example.com", "123456")
        ev_repo.update.assert_awaited_once_with(record)


@pytest.mark.asyncio
class TestRegister:
    async def test_raises_user_001_when_email_already_exists(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = _mock_user()
        data = RegisterReq(
            role="REVIEWER",
            username="Alice",
            email="taken@example.com",
            password="pw",
        )
        with pytest.raises(AppException) as exc:
            await service.register(data)
        assert exc.value.code == USER_001.code

    async def test_password_is_hashed_before_save(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        user_repo.save = AsyncMock(return_value=_mock_user(email="new@example.com"))
        data = RegisterReq(
            role="REVIEWER",
            username="Bob",
            email="new@example.com",
            password="plain",
        )
        await service.register(data)
        saved = user_repo.save.call_args[0][0]
        assert saved.password_hash != "plain"
        assert verify_password("plain", saved.password_hash)

    async def test_returns_user_and_two_jwt_tokens(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        expected_user = _mock_user(email="new@example.com")
        user_repo.save = AsyncMock(return_value=expected_user)
        data = RegisterReq(
            role="REVIEWER",
            username="Bob",
            email="new@example.com",
            password="pw",
        )
        user, access_token, refresh_token = await service.register(data)
        assert user is expected_user
        assert isinstance(access_token, str) and len(access_token) > 10
        assert isinstance(refresh_token, str) and len(refresh_token) > 10

    async def test_access_token_encodes_correct_user_id(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        saved_user = _mock_user()
        user_repo.save = AsyncMock(return_value=saved_user)
        data = RegisterReq(
            role="REVIEWER",
            username="Bob",
            email="new@example.com",
            password="pw",
        )
        _, access_token, _ = await service.register(data)
        assert decode_token(access_token) == str(saved_user.id)


@pytest.mark.asyncio
class TestRefreshAccessToken:
    def test_raises_auth_001_on_malformed_token(self) -> None:
        service, _, _, _ = _make_service()
        with pytest.raises(AppException) as exc:
            service.refresh_access_token("not.a.jwt")
        assert exc.value.code == AUTH_001.code

    def test_returns_valid_access_token_for_valid_refresh(self) -> None:
        service, _, _, _ = _make_service()
        from app.core.security import create_refresh_token

        uid = str(uuid4())
        refresh = create_refresh_token(uid)
        access = service.refresh_access_token(refresh)
        assert decode_token(access) == uid


@pytest.mark.asyncio
class TestLogin:
    async def test_raises_auth_002_when_user_not_found(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        data = LoginReq(role="REVIEWER", mail="ghost@example.com", password="pw")
        with pytest.raises(AppException) as exc:
            await service.login(data)
        assert exc.value.code == AUTH_002.code

    async def test_raises_auth_002_on_wrong_password(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = _mock_user(password="correct")
        data = LoginReq(role="REVIEWER", mail="u@example.com", password="wrong")
        with pytest.raises(AppException) as exc:
            await service.login(data)
        assert exc.value.code == AUTH_002.code

    async def test_raises_auth_002_on_role_mismatch(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = _mock_user(role="OWNER", password="pw")
        data = LoginReq(role="REVIEWER", mail="u@example.com", password="pw")
        with pytest.raises(AppException) as exc:
            await service.login(data)
        assert exc.value.code == AUTH_002.code

    async def test_returns_user_and_tokens_on_success(self) -> None:
        service, user_repo, _, _ = _make_service()
        user = _mock_user(role="OWNER", password="pw")
        user_repo.find_by_email.return_value = user
        data = LoginReq(role="OWNER", mail="u@example.com", password="pw")
        result_user, access, refresh = await service.login(data)
        assert result_user is user
        assert decode_token(access) == str(user.id)
        assert isinstance(refresh, str) and len(refresh) > 10


@pytest.mark.asyncio
class TestChangePassword:
    async def test_raises_auth_002_when_user_not_found(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_id.return_value = None
        with pytest.raises(AppException) as exc:
            await service.change_password("uid", "old", "new")
        assert exc.value.code == AUTH_002.code

    async def test_raises_auth_002_on_wrong_old_password(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_id.return_value = _mock_user(password="correct")
        with pytest.raises(AppException) as exc:
            await service.change_password("uid", "wrong", "new")
        assert exc.value.code == AUTH_002.code

    async def test_updates_password_hash_to_new_password(self) -> None:
        service, user_repo, _, _ = _make_service()
        user = _mock_user(password="oldpass")
        user_repo.find_by_id.return_value = user
        await service.change_password("uid", "oldpass", "newpass")
        assert verify_password("newpass", user.password_hash)
        assert not verify_password("oldpass", user.password_hash)

    async def test_calls_repo_save_after_update(self) -> None:
        service, user_repo, _, _ = _make_service()
        user = _mock_user(password="oldpass")
        user_repo.find_by_id.return_value = user
        await service.change_password("uid", "oldpass", "newpass")
        user_repo.save.assert_awaited_once_with(user)


@pytest.mark.asyncio
class TestResetPassword:
    async def test_raises_user_002_when_user_not_found(self) -> None:
        service, user_repo, _, _ = _make_service()
        user_repo.find_by_email.return_value = None
        data = ResetPasswordReq(email="ghost@example.com")
        with pytest.raises(AppException) as exc:
            await service.reset_password(data)
        assert exc.value.code == USER_002.code

    async def test_changes_password_hash(self) -> None:
        service, user_repo, _, _ = _make_service()
        user = _mock_user()
        original_hash = user.password_hash
        user_repo.find_by_email.return_value = user
        data = ResetPasswordReq(email="u@example.com")
        await service.reset_password(data)
        assert user.password_hash != original_hash

    async def test_new_password_hash_is_verifiable(self) -> None:
        service, user_repo, _, _ = _make_service()
        user = _mock_user()
        user_repo.find_by_email.return_value = user
        data = ResetPasswordReq(email="u@example.com")
        await service.reset_password(data)
        assert user.password_hash.startswith("$2b$")

    async def test_sends_email_to_the_user(self) -> None:
        service, user_repo, _, email_sender = _make_service()
        user = _mock_user(email="reset@example.com")
        user_repo.find_by_email.return_value = user
        data = ResetPasswordReq(email="reset@example.com")
        await service.reset_password(data)
        email_sender.send.assert_awaited_once()
        assert email_sender.send.call_args[0][0] == "reset@example.com"
