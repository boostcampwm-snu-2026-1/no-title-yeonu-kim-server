from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    async def send_verification(self, to: str, code: str) -> None: ...

    @abstractmethod
    async def send_temp_password(self, to: str, temp_password: str) -> None: ...

    @abstractmethod
    async def send_reward(
        self,
        to: str,
        event_title: str,
        reward_wei: int,
        wallet_balance_wei: int,
    ) -> None: ...
