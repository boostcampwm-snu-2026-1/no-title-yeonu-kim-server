from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("event_id", "reviewer_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    wallet_address: Mapped[str] = mapped_column(String)
    image_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "APPROVED", "REJECTED", name="application_status"),
        default="PENDING",
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
