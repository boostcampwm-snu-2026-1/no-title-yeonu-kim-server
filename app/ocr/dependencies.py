from app.ocr.service import OCRService
from app.ocr.service_impl import OCRServiceImpl


def get_ocr_service() -> OCRService:
    return OCRServiceImpl()
