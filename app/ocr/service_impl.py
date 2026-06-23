import base64
import logging
from typing import Literal, cast

import anthropic

from app.core.config import settings
from app.ocr.service import OCRService

logger = logging.getLogger(__name__)

_MediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
_SUPPORTED_MEDIA_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)


def _to_media_type(content_type: str) -> _MediaType:
    if content_type in _SUPPORTED_MEDIA_TYPES:
        return cast(_MediaType, content_type)
    return "image/jpeg"


class OCRServiceImpl(OCRService):
    async def check_condition(
        self, image_bytes: bytes, content_type: str, condition: str
    ) -> bool:
        media_type = _to_media_type(content_type)
        encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-opus-4-8",
            max_tokens=128,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                f"이미지가 아래 조건을 충족하는지 판단하세요.\n"
                                f"조건: {condition}\n\n"
                                "충족하면 'PASS', 충족하지 않으면 'FAIL'로만 응답하세요."  # noqa: E501
                            ),
                        },
                    ],
                }
            ],
        )

        block = response.content[0]
        verdict = (
            block.text.strip()
            if isinstance(block, anthropic.types.TextBlock)
            else "(non-text block)"
        )
        logger.warning("[OCR] condition=%r verdict=%r", condition, verdict)
        return (
            isinstance(block, anthropic.types.TextBlock)
            and "FAIL" not in block.text.upper()
        )
