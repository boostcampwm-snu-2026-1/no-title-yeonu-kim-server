from fastapi import status
from fastapi.exceptions import HTTPException


class ImageConditionNotMetError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="이미지가 이벤트 조건을 충족하지 않습니다.",
        )
