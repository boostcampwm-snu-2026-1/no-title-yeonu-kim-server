from abc import ABC, abstractmethod


class BlockchainService(ABC):
    @abstractmethod
    async def deploy_contract(self) -> str: ...

    @abstractmethod
    async def fund_contract(self, contract_address: str, amount_wei: int) -> str: ...

    @abstractmethod
    async def payout(
        self, contract_address: str, recipient: str, amount_wei: int
    ) -> str: ...

    @abstractmethod
    async def get_wallet_balance(self, address: str) -> int: ...

    @abstractmethod
    async def payout_safe(
        self,
        contract_address: str,
        recipient: str,
        amount_wei: int,
        reviewer_email: str,
        event_title: str,
    ) -> None: ...
