"""Unit tests for app/services/deposit.py — AsyncSession is mocked."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import GEN_003_AMOUNT, AppException
from app.schemas.deposit import DepositReq
from app.services.deposit import create_deposit


def _make_mock_deposit(*, amount: int, balance: int) -> MagicMock:
    dep = MagicMock()
    dep.amount = amount
    dep.balance = balance
    dep.deposited_at = datetime.now(UTC)
    return dep


@pytest.mark.asyncio
class TestCreateDeposit:
    async def test_raises_gen_003_amount_when_zero(self) -> None:
        db = AsyncMock()
        with pytest.raises(AppException) as exc:
            await create_deposit(db, str(uuid4()), DepositReq(amount=0))
        assert exc.value.code == GEN_003_AMOUNT.code
        assert exc.value.status_code == 400

    async def test_raises_gen_003_amount_when_negative(self) -> None:
        db = AsyncMock()
        with pytest.raises(AppException) as exc:
            await create_deposit(db, str(uuid4()), DepositReq(amount=-1))
        assert exc.value.code == GEN_003_AMOUNT.code

    async def test_no_db_access_before_amount_validation(self) -> None:
        db = AsyncMock()
        with pytest.raises(AppException):
            await create_deposit(db, str(uuid4()), DepositReq(amount=0))
        db.scalar.assert_not_awaited()

    async def test_first_deposit_balance_equals_amount(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 0
        mock_deposit = _make_mock_deposit(amount=1000, balance=1000)
        with patch("app.services.deposit.Deposit", return_value=mock_deposit):
            result = await create_deposit(db, str(uuid4()), DepositReq(amount=1000))
        assert result.balance == 1000

    async def test_subsequent_deposit_accumulates_balance(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 5000  # existing max balance
        mock_deposit = _make_mock_deposit(amount=3000, balance=8000)
        with patch("app.services.deposit.Deposit") as MockDeposit:
            MockDeposit.return_value = mock_deposit
            result = await create_deposit(db, str(uuid4()), DepositReq(amount=3000))
        call_kwargs = MockDeposit.call_args.kwargs
        assert call_kwargs["amount"] == 3000
        assert call_kwargs["balance"] == 8000
        assert result.balance == 8000

    async def test_deposit_uses_correct_user_id(self) -> None:
        user_id = uuid4()
        db = AsyncMock()
        db.scalar.return_value = 0
        mock_deposit = _make_mock_deposit(amount=500, balance=500)
        with patch("app.services.deposit.Deposit") as MockDeposit:
            MockDeposit.return_value = mock_deposit
            await create_deposit(db, str(user_id), DepositReq(amount=500))
        call_kwargs = MockDeposit.call_args.kwargs
        assert call_kwargs["user_id"] == user_id

    async def test_response_contains_deposited_at_timestamp(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 0
        mock_deposit = _make_mock_deposit(amount=100, balance=100)
        with patch("app.services.deposit.Deposit", return_value=mock_deposit):
            result = await create_deposit(db, str(uuid4()), DepositReq(amount=100))
        assert isinstance(result.depositedAt, str)
        assert "T" in result.depositedAt  # ISO 8601 format

    async def test_calls_commit_and_refresh(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 0
        mock_deposit = _make_mock_deposit(amount=100, balance=100)
        with patch("app.services.deposit.Deposit", return_value=mock_deposit):
            await create_deposit(db, str(uuid4()), DepositReq(amount=100))
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_none_current_balance_treated_as_zero(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = None  # real DB returns 0 via COALESCE
        mock_deposit = _make_mock_deposit(amount=200, balance=200)
        with patch("app.services.deposit.Deposit") as MockDeposit:
            MockDeposit.return_value = mock_deposit
            await create_deposit(db, str(uuid4()), DepositReq(amount=200))
        call_kwargs = MockDeposit.call_args.kwargs
        assert call_kwargs["balance"] == 200  # (None or 0) + 200 = 200
