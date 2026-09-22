import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuspg.db.base import Base

flag_tags = Table(
    "flag_tags",
    Base.metadata,
    Column("flag_id", ForeignKey("flags.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    environments: Mapped[list["Environment"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Environment.name",
    )
    flags: Mapped[list["Flag"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Flag.name",
    )


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_project_env_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    project: Mapped["Project"] = relationship(back_populates="environments")
    flag_states: Mapped[list["FlagEnvironmentState"]] = relationship(
        back_populates="environment",
        cascade="all, delete-orphan",
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#4f46e5", nullable=False)

    flags: Mapped[list["Flag"]] = relationship(
        secondary=flag_tags,
        back_populates="tags",
    )


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_project_flag_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flag_type: Mapped[str] = mapped_column(String(32), default="boolean", nullable=False)
    default_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="flags")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=flag_tags,
        back_populates="flags",
        order_by="Tag.name",
    )
    flag_states: Mapped[list["FlagEnvironmentState"]] = relationship(
        back_populates="flag",
        cascade="all, delete-orphan",
    )


class FlagEnvironmentState(Base):
    __tablename__ = "flag_environment_states"
    __table_args__ = (
        UniqueConstraint("flag_id", "environment_id", name="uq_flag_environment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flags.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    variant_value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    flag: Mapped["Flag"] = relationship(back_populates="flag_states")
    environment: Mapped["Environment"] = relationship(back_populates="flag_states")
    rules: Mapped[list["TargetingRule"]] = relationship(
        back_populates="flag_environment",
        cascade="all, delete-orphan",
        order_by="TargetingRule.priority",
    )


class TargetingRule(Base):
    __tablename__ = "targeting_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    flag_environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flag_environment_states.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    serve_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    flag_environment: Mapped["FlagEnvironmentState"] = relationship(back_populates="rules")
    conditions: Mapped[list["RuleCondition"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class RuleCondition(Base):
    __tablename__ = "rule_conditions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("targeting_rules.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(32), nullable=False)
    values: Mapped[Any] = mapped_column(JSON, nullable=False)

    rule: Mapped["TargetingRule"] = relationship(back_populates="conditions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    changes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
