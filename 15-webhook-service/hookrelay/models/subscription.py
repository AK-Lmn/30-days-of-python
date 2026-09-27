import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hookrelay.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"sub_{uuid.uuid4().hex[:16]}",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
    secret_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: f"whsec_{uuid.uuid4().hex}",
    )
    event_patterns: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["*"],
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    backoff_base_seconds: Mapped[float] = mapped_column(
        Float,
        default=2.0,
        nullable=False,
    )
    timeout_seconds: Mapped[float] = mapped_column(
        Float,
        default=10.0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    deliveries: Mapped[list["Delivery"]] = relationship(
        "Delivery",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )
