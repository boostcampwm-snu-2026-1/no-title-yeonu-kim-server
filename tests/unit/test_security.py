"""Unit tests for app/core/security.py — pure functions, no DB or network."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import jwt.exceptions
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        hashed = get_password_hash("secret")
        assert verify_password("secret", hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = get_password_hash("secret")
        assert verify_password("wrong", hashed) is False

    def test_empty_string_matches_empty_hash(self) -> None:
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False


class TestGetPasswordHash:
    def test_returns_bcrypt_prefix(self) -> None:
        assert get_password_hash("pw").startswith("$2b$")

    def test_same_password_produces_different_hashes(self) -> None:
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2

    def test_hash_is_verifiable(self) -> None:
        hashed = get_password_hash("mypassword")
        assert verify_password("mypassword", hashed)
        assert not verify_password("other", hashed)


class TestCreateAccessToken:
    def test_returns_decodable_jwt_with_correct_sub(self) -> None:
        token = create_access_token("user-abc")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user-abc"

    def test_expires_in_approximately_30_minutes(self) -> None:
        token = create_access_token("uid")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        delta = exp - datetime.now(UTC)
        assert timedelta(minutes=29) < delta < timedelta(minutes=31)

    def test_accepts_uuid_string_and_decode_returns_it(self) -> None:
        uid = str(uuid4())
        token = create_access_token(uid)
        assert decode_token(token) == uid


class TestCreateRefreshToken:
    def test_returns_decodable_jwt_with_correct_sub(self) -> None:
        token = create_refresh_token("user-xyz")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user-xyz"

    def test_expires_in_approximately_7_days(self) -> None:
        token = create_refresh_token("uid")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        delta = exp - datetime.now(UTC)
        assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)

    def test_longer_lived_than_access_token(self) -> None:
        access = create_access_token("uid")
        refresh = create_refresh_token("uid")
        access_payload = jwt.decode(access, settings.secret_key, algorithms=["HS256"])
        refresh_payload = jwt.decode(refresh, settings.secret_key, algorithms=["HS256"])
        assert refresh_payload["exp"] > access_payload["exp"]


class TestCreateVerificationToken:
    def test_includes_email_as_sub(self) -> None:
        token = create_verification_token("user@example.com")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user@example.com"

    def test_includes_email_verification_type_field(self) -> None:
        token = create_verification_token("user@example.com")
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload.get("type") == "email_verification"


class TestDecodeToken:
    def test_decodes_valid_access_token(self) -> None:
        uid = str(uuid4())
        token = create_access_token(uid)
        assert decode_token(token) == uid

    def test_raises_on_garbage_string(self) -> None:
        with pytest.raises(jwt.exceptions.DecodeError):
            decode_token("not.a.jwt.at.all")

    def test_raises_on_expired_token(self) -> None:
        payload = {
            "sub": "uid",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired = str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            decode_token(expired)

    def test_raises_on_wrong_secret(self) -> None:
        payload = {"sub": "uid", "exp": datetime.now(UTC) + timedelta(minutes=30)}
        token = str(jwt.encode(payload, "wrong-secret", algorithm="HS256"))
        with pytest.raises(jwt.exceptions.InvalidSignatureError):
            decode_token(token)
