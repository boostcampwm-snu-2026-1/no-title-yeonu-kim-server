"""
Unit tests for app/blockchain/service_impl.py.
All web3 network calls are mocked — no live node required.
"""

import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.blockchain.service_impl as bc_module
from app.blockchain.service_impl import BlockchainServiceImpl

FAKE_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "release",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]
FAKE_BYTECODE = "0x6080604052"
FAKE_TX_HASH = bytes.fromhex("ab" * 32)
FAKE_CONTRACT_ADDRESS = "0xDeAdBeEf00000000000000000000000000001234"
FAKE_WALLET = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
FAKE_PRIVATE_KEY = "0x" + "a" * 64


@pytest.fixture(autouse=True)
def reset_cache() -> Generator[None, None, None]:
    """Ensure the module-level artifact cache is cleared between tests."""
    bc_module._artifact_cache = None
    yield
    bc_module._artifact_cache = None


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    p = tmp_path / "ReviewReward.json"
    p.write_text(json.dumps({"abi": FAKE_ABI, "bytecode": {"object": FAKE_BYTECODE}}))
    return p


@pytest.fixture
def patched_settings(artifact: Path) -> Generator[MagicMock, None, None]:
    with patch("app.blockchain.service_impl.settings") as s:
        s.contract_artifact_path = str(artifact)
        s.blockchain_rpc_url = "http://localhost:8545"
        s.server_private_key = FAKE_PRIVATE_KEY
        yield s


def make_w3_mock(
    contract_address: str = FAKE_CONTRACT_ADDRESS,
) -> MagicMock:
    """Build a minimal AsyncWeb3 mock covering both deploy and payout paths."""
    account = MagicMock()
    account.address = "0x" + "1" * 40
    account.sign_transaction.return_value = MagicMock(raw_transaction=b"signed_tx")

    # deploy path: contract.constructor().build_transaction(...)
    mock_contract = MagicMock()
    mock_contract.constructor.return_value.build_transaction = AsyncMock(
        return_value={"from": account.address, "nonce": 0, "gas": 500_000}
    )

    # payout path: contract.functions.release(recipient, amount).build_transaction(...)
    release_call = MagicMock()
    release_call.build_transaction = AsyncMock(
        return_value={"from": account.address, "nonce": 0, "gas": 100_000}
    )
    mock_contract.functions.release.return_value = release_call

    w3 = MagicMock()
    w3.eth.account.from_key.return_value = account
    w3.eth.contract.return_value = mock_contract
    w3.eth.get_transaction_count = AsyncMock(return_value=0)
    w3.eth.send_raw_transaction = AsyncMock(return_value=FAKE_TX_HASH)
    w3.eth.wait_for_transaction_receipt = AsyncMock(
        return_value={"contractAddress": contract_address}
    )
    w3.eth.get_balance = AsyncMock(return_value=0)
    return w3


# ---------------------------------------------------------------------------
# deploy_contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeployContract:
    async def test_returns_contract_address(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            result = await BlockchainServiceImpl().deploy_contract()
        assert result == FAKE_CONTRACT_ADDRESS

    async def test_uses_500k_gas(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().deploy_contract()

        build_tx = (
            w3.eth.contract.return_value.constructor.return_value.build_transaction
        )
        tx_kwargs: dict[str, Any] = build_tx.call_args[0][0]
        assert tx_kwargs["gas"] == 500_000

    async def test_logs_deployed_address(
        self, patched_settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
            caplog.at_level(logging.INFO, logger="app.blockchain.service_impl"),
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().deploy_contract()
        assert FAKE_CONTRACT_ADDRESS in caplog.text

    async def test_artifact_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        with patch("app.blockchain.service_impl.settings") as s:
            s.contract_artifact_path = str(tmp_path / "nonexistent.json")
            s.blockchain_rpc_url = "http://localhost:8545"
            s.server_private_key = FAKE_PRIVATE_KEY
            with pytest.raises(FileNotFoundError):
                await BlockchainServiceImpl().deploy_contract()

    async def test_sends_raw_transaction(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().deploy_contract()
        w3.eth.send_raw_transaction.assert_awaited_once_with(b"signed_tx")


# ---------------------------------------------------------------------------
# payout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPayout:
    async def test_returns_tx_hash_hex(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            result = await BlockchainServiceImpl().payout(
                FAKE_CONTRACT_ADDRESS, FAKE_WALLET, 1_000_000
            )
        assert result == FAKE_TX_HASH.hex()

    async def test_release_called_with_correct_args(
        self, patched_settings: MagicMock
    ) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().payout(
                FAKE_CONTRACT_ADDRESS, FAKE_WALLET, 999
            )
        w3.eth.contract.return_value.functions.release.assert_called_once_with(
            FAKE_WALLET, 999
        )

    async def test_uses_100k_gas(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().payout(FAKE_CONTRACT_ADDRESS, FAKE_WALLET, 1)

        release_call = w3.eth.contract.return_value.functions.release.return_value
        tx_kwargs: dict[str, Any] = release_call.build_transaction.call_args[0][0]
        assert tx_kwargs["gas"] == 100_000

    async def test_logs_tx_hash(
        self, patched_settings: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
            caplog.at_level(logging.INFO, logger="app.blockchain.service_impl"),
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().payout(FAKE_CONTRACT_ADDRESS, FAKE_WALLET, 1)
        assert FAKE_TX_HASH.hex() in caplog.text


# ---------------------------------------------------------------------------
# payout_safe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPayoutSafe:
    async def test_success_does_not_raise(self, patched_settings: MagicMock) -> None:
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
            patch("app.blockchain.service_impl.send_email", new_callable=AsyncMock),
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().payout_safe(
                FAKE_CONTRACT_ADDRESS,
                FAKE_WALLET,
                1_000,
                "test@example.com",
                "Test Event",
            )

    async def test_exception_is_swallowed(self) -> None:
        service = BlockchainServiceImpl()
        with patch.object(
            BlockchainServiceImpl,
            "payout",
            new_callable=AsyncMock,
            side_effect=RuntimeError("node down"),
        ):
            await service.payout_safe(
                FAKE_CONTRACT_ADDRESS,
                FAKE_WALLET,
                1_000,
                "test@example.com",
                "Test Event",
            )

    async def test_exception_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        service = BlockchainServiceImpl()
        with (
            patch.object(
                BlockchainServiceImpl,
                "payout",
                new_callable=AsyncMock,
                side_effect=RuntimeError("connection refused"),
            ),
            caplog.at_level(logging.ERROR, logger="app.blockchain.service_impl"),
        ):
            await service.payout_safe(
                FAKE_CONTRACT_ADDRESS,
                FAKE_WALLET,
                1_000,
                "test@example.com",
                "Test Event",
            )
        assert "payout failed" in caplog.text
        assert FAKE_CONTRACT_ADDRESS in caplog.text


# ---------------------------------------------------------------------------
# artifact caching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestArtifactCache:
    async def test_cache_populated_after_first_call(
        self, patched_settings: MagicMock
    ) -> None:
        """_artifact_cache must be None before first call and set after."""
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            assert bc_module._artifact_cache is None
            await BlockchainServiceImpl().deploy_contract()
        assert bc_module._artifact_cache is not None

    async def test_second_call_reuses_cache(self, patched_settings: MagicMock) -> None:
        """A second deploy_contract() must return the same cached ABI object."""
        w3 = make_w3_mock()
        with (
            patch("app.blockchain.service_impl._make_w3", return_value=w3),
            patch("app.blockchain.service_impl.AsyncWeb3") as mock_cls,
        ):
            mock_cls.to_checksum_address.side_effect = lambda a: a
            await BlockchainServiceImpl().deploy_contract()
            cache_after_first = bc_module._artifact_cache
            await BlockchainServiceImpl().deploy_contract()
        assert bc_module._artifact_cache is cache_after_first
