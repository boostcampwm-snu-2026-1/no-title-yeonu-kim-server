"""
Ethereum blockchain service for ReviewReward contract interaction.

Contract source (Solidity ^0.8.0):

    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    contract ReviewReward {
        address public owner;

        constructor() { owner = msg.sender; }

        receive() external payable {}

        /// Called by the server to pay a reviewer.
        /// @param recipient  Reviewer's wallet address.
        /// @param amount     Amount in Wei.
        function release(address payable recipient, uint256 amount) external {
            require(msg.sender == owner, "Not authorized");
            require(address(this).balance >= amount, "Insufficient balance");
            recipient.transfer(amount);
        }

        function getBalance() external view returns (uint256) {
            return address(this).balance;
        }
    }

Build with Foundry: `forge build`
Artifact: out/ReviewReward.sol/ReviewReward.json
"""

import json
import logging
from pathlib import Path
from typing import Any

from web3 import AsyncWeb3

from app.core.config import settings
from app.email.service_impl import send_email

logger = logging.getLogger(__name__)

_artifact_cache: tuple[list[dict[str, Any]], str] | None = None


def _load_artifact() -> tuple[list[dict[str, Any]], str]:
    global _artifact_cache
    if _artifact_cache is None:
        path = Path(settings.contract_artifact_path)
        with path.open() as f:
            artifact = json.load(f)
        abi: list[dict[str, Any]] = artifact["abi"]
        bytecode: str = artifact["bytecode"]["object"]
        _artifact_cache = abi, bytecode
    return _artifact_cache


def _make_w3() -> "AsyncWeb3[Any]":
    return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(settings.blockchain_rpc_url))


async def deploy_contract() -> str:
    """Deploy a new ReviewReward contract. Returns the deployed contract address."""
    w3 = _make_w3()
    abi, bytecode = _load_artifact()
    account = w3.eth.account.from_key(settings.server_private_key)

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = await w3.eth.get_transaction_count(account.address)
    tx = await contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gas": 500_000,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)

    address = str(receipt["contractAddress"])
    logger.info("[BLOCKCHAIN] deployed contract=%s tx=%s", address, tx_hash.hex())
    return address


async def fund_contract(contract_address: str, amount_wei: int) -> str:
    """Send ETH to the contract. Returns tx hash."""
    w3 = _make_w3()
    account = w3.eth.account.from_key(settings.server_private_key)

    nonce = await w3.eth.get_transaction_count(account.address)
    tx = {
        "from": account.address,
        "to": AsyncWeb3.to_checksum_address(contract_address),
        "value": amount_wei,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": await w3.eth.gas_price,
    }
    signed = account.sign_transaction(tx)
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    await w3.eth.wait_for_transaction_receipt(tx_hash)

    tx_hex = tx_hash.hex()
    logger.info(
        "[BLOCKCHAIN] funded contract=%s amount_wei=%d tx=%s",
        contract_address,
        amount_wei,
        tx_hex,
    )
    return tx_hex


async def payout(contract_address: str, recipient: str, amount_wei: int) -> str:
    """Call release() on the ReviewReward contract. Returns tx hash."""
    w3 = _make_w3()
    abi, _ = _load_artifact()
    account = w3.eth.account.from_key(settings.server_private_key)

    contract = w3.eth.contract(
        address=AsyncWeb3.to_checksum_address(contract_address),
        abi=abi,
    )
    nonce = await w3.eth.get_transaction_count(account.address)
    tx = await contract.functions.release(
        AsyncWeb3.to_checksum_address(recipient),
        amount_wei,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gas": 100_000,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()

    logger.info(
        "[BLOCKCHAIN] payout sent contract=%s recipient=%s amount_wei=%d tx=%s",
        contract_address,
        recipient,
        amount_wei,
        tx_hex,
    )
    return tx_hex


async def get_wallet_balance(address: str) -> int:
    """Return the ETH balance of a wallet address in wei."""
    w3 = _make_w3()
    return await w3.eth.get_balance(AsyncWeb3.to_checksum_address(address))


async def payout_safe(
    contract_address: str,
    recipient: str,
    amount_wei: int,
    reviewer_email: str,
    event_title: str,
) -> None:
    """BackgroundTasks wrapper — logs errors instead of raising."""
    try:
        await payout(contract_address, recipient, amount_wei)
        wallet_balance = await get_wallet_balance(recipient)
        reward_eth = amount_wei / 10**18
        balance_eth = wallet_balance / 10**18
        subject = "[VLSI] 리워드 지급 완료"
        body = f"""
    <p>안녕하세요,</p>
    <p>스마트컨트랙트를 통한 리워드 지급이 완료되었습니다.</p>
    <table style="border-collapse:collapse;margin-top:12px">
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">지급 이벤트</td>
        <td style="padding:8px 0"><strong>{event_title}</strong></td>
      </tr>
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">지급 금액</td>
        <td style="padding:8px 0"><strong>{reward_eth:.6f} ETH</strong></td>
      </tr>
      <tr>
        <td style="padding:8px 16px 8px 0;color:#666">현재 지갑 잔액</td>
        <td style="padding:8px 0"><strong>{balance_eth:.6f} ETH</strong></td>
      </tr>
    </table>
    <p style="margin-top:16px;color:#888;font-size:12px">
      본 메일은 자동 발송된 메일입니다.
    </p>
    """
        await send_email(reviewer_email, subject, body)
    except Exception:
        logger.exception(
            "[BLOCKCHAIN] payout failed contract=%s recipient=%s amount_wei=%d",
            contract_address,
            recipient,
            amount_wei,
        )
