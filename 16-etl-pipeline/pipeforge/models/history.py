from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String(36), primary_key=True)
    pipeline_name = Column(String(128), nullable=False)
    source_uri = Column(String(512), nullable=True)
    destination_uri = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")
    records_read = Column(Integer, default=0)
    records_valid = Column(Integer, default=0)
    records_invalid = Column(Integer, default=0)
    records_transformed = Column(Integer, default=0)
    records_loaded = Column(Integer, default=0)
    records_quarantined = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    quarantined_records = relationship(
        "QuarantinedRecord",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    row_number = Column(Integer, default=0)
    raw_data = Column(Text, nullable=False)
    errors = Column(Text, nullable=False)
    quarantined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("PipelineRun", back_populates="quarantined_records")
