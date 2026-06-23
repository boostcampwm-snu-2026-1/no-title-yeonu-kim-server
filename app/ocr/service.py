from abc import ABC, abstractmethod


class OCRService(ABC):
    @abstractmethod
    async def check_condition(
        self, image_bytes: bytes, content_type: str, condition: str
    ) -> bool: ...
