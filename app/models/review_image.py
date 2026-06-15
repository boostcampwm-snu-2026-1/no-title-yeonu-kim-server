from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewImage(Base):
    __tablename__ = "review_images"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("review_submissions.id"))
    image_key: Mapped[str] = mapped_column(String)
    order: Mapped[int] = mapped_column(Integer)
