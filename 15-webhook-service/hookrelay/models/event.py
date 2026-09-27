import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hookrelay.database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"evt_{uuid.uuid4().hex[:16]}",
    )
    endpoint_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        default="unknown",
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    raw_body: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    headers: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    endpoint: Mapped["Endpoint"] = relationship(
        "Endpoint",
        back_populates="events",
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        "Delivery",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_endpoint_idempotency", "endpoint_id", "idempotency_key"),
    )
