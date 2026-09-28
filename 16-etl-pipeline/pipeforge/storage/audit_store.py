import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session
from pipeforge.config import settings
from pipeforge.models.history import Base, PipelineRun, QuarantinedRecord
from pipeforge.models.metrics import PipelineMetrics
from pipeforge.models.enums import PipelineStatus


class AuditStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or settings.metadata_database_url
        self.engine = create_engine(self.database_url, echo=False)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.initialize()

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def create_run(
        self,
        run_id: str,
        pipeline_name: str,
        source_uri: str = "",
        destination_uri: str = "",
    ) -> PipelineRun:
        with self.session_factory() as session:
            run = PipelineRun(
                id=run_id,
                pipeline_name=pipeline_name,
                source_uri=source_uri,
                destination_uri=destination_uri,
                status=PipelineStatus.RUNNING.value,
                started_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def finish_run(
        self,
        run_id: str,
        status: PipelineStatus,
        metrics: PipelineMetrics,
        error_message: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            run = session.get(PipelineRun, run_id)
            if run:
                run.status = status.value
                run.records_read = metrics.records_read
                run.records_valid = metrics.records_valid
                run.records_invalid = metrics.records_invalid
                run.records_transformed = metrics.records_transformed
                run.records_loaded = metrics.records_loaded
                run.records_quarantined = metrics.records_quarantined
                run.records_skipped = metrics.records_skipped
                run.completed_at = metrics.end_time or datetime.now(timezone.utc)
                run.duration_seconds = metrics.duration_seconds
                run.error_message = error_message
                session.commit()

    def save_quarantined_record(
        self,
        run_id: str,
        row_number: int,
        raw_data: dict[str, Any],
        errors: list[str],
    ) -> None:
        with self.session_factory() as session:
            item = QuarantinedRecord(
                run_id=run_id,
                row_number=row_number,
                raw_data=json.dumps(raw_data, default=str),
                errors=json.dumps(errors),
                quarantined_at=datetime.now(timezone.utc),
            )
            session.add(item)
            session.commit()

    def get_run(self, run_id: str) -> PipelineRun | None:
        with self.session_factory() as session:
            return session.get(PipelineRun, run_id)

    def list_runs(self, limit: int = 50) -> list[PipelineRun]:
        with self.session_factory() as session:
            stmt = select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit)
            return list(session.scalars(stmt).all())

    def get_quarantined_records(self, run_id: str) -> list[QuarantinedRecord]:
        with self.session_factory() as session:
            stmt = select(QuarantinedRecord).where(QuarantinedRecord.run_id == run_id).order_by(QuarantinedRecord.row_number)
            return list(session.scalars(stmt).all())

    def export_quarantine_to_json(self, run_id: str, destination_path: Path | str) -> int:
        records = self.get_quarantined_records(run_id)
        out_path = Path(destination_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "row_number": r.row_number,
                "raw_data": json.loads(r.raw_data),
                "errors": json.loads(r.errors),
                "quarantined_at": r.quarantined_at.isoformat() if r.quarantined_at else None,
            }
            for r in records
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return len(records)
