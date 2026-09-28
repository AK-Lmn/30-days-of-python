import uuid
from typing import Callable
from pipeforge.extractors.base import BaseExtractor
from pipeforge.validators.base import BaseValidator
from pipeforge.validators.quality_gate import QualityGate
from pipeforge.transformers.base import BaseTransformer
from pipeforge.transformers.chain import TransformerChain
from pipeforge.transformers.aggregator import BatchAggregator
from pipeforge.loaders.base import BaseLoader
from pipeforge.storage.audit_store import AuditStore
from pipeforge.models.record import Record
from pipeforge.models.metrics import PipelineMetrics
from pipeforge.models.enums import ErrorStrategy, PipelineStatus


class PipelineError(Exception):
    pass


class ETLPipeline:
    def __init__(
        self,
        name: str,
        extractor: BaseExtractor,
        loaders: list[BaseLoader] | BaseLoader,
        validators: list[BaseValidator] | None = None,
        transformers: list[BaseTransformer] | None = None,
        aggregator: BatchAggregator | None = None,
        quality_gate: QualityGate | None = None,
        audit_store: AuditStore | None = None,
        error_strategy: ErrorStrategy = ErrorStrategy.QUARANTINE,
        batch_size: int = 500,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        self.name = name
        self.extractor = extractor
        self.loaders = loaders if isinstance(loaders, list) else [loaders]
        self.validators = validators or []
        self.transformers = transformers or []
        self.transformer_chain = TransformerChain(self.transformers)
        self.aggregator = aggregator
        self.quality_gate = quality_gate
        self.audit_store = audit_store or AuditStore()
        self.error_strategy = error_strategy
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.run_id = str(uuid.uuid4())

    def run(self) -> PipelineMetrics:
        metrics = PipelineMetrics()
        extractor_meta = self.extractor.get_metadata()
        source_uri = extractor_meta.get("file_path") or extractor_meta.get("endpoint_url") or extractor_meta.get("connection_url") or ""
        dest_uris = [l.get_metadata().get("file_path") or l.get_metadata().get("table_name") or l.get_metadata().get("endpoint_url") or "" for l in self.loaders]
        dest_uri_str = ", ".join(d for d in dest_uris if d)

        self.audit_store.create_run(
            run_id=self.run_id,
            pipeline_name=self.name,
            source_uri=source_uri,
            destination_uri=dest_uri_str,
        )

        for loader in self.loaders:
            loader.initialize()

        run_status = PipelineStatus.SUCCESS
        error_message = None
        all_processed_records: list[Record] = []

        try:
            batch: list[Record] = []

            for record in self.extractor.extract():
                metrics.records_read += 1
                batch.append(record)

                if len(batch) >= self.batch_size:
                    self._process_batch(batch, metrics, all_processed_records)
                    batch = []
                    if self.progress_callback:
                        self.progress_callback(metrics.records_read, metrics.records_loaded)

            if batch:
                self._process_batch(batch, metrics, all_processed_records)
                if self.progress_callback:
                    self.progress_callback(metrics.records_read, metrics.records_loaded)

            if self.aggregator and all_processed_records:
                aggregated = self.aggregator.aggregate(all_processed_records)
                for loader in self.loaders:
                    loaded_count = loader.load(aggregated)
                    metrics.records_loaded = loaded_count

            if self.quality_gate:
                passed, violations = self.quality_gate.evaluate(metrics, all_processed_records)
                if not passed:
                    run_status = PipelineStatus.FAILED
                    error_message = "; ".join(violations)

            if run_status == PipelineStatus.SUCCESS and metrics.records_invalid > 0:
                run_status = PipelineStatus.PARTIAL

        except Exception as exc:
            run_status = PipelineStatus.FAILED
            error_message = str(exc)
            metrics.finish()
            self.audit_store.finish_run(
                run_id=self.run_id,
                status=run_status,
                metrics=metrics,
                error_message=error_message,
            )
            for loader in self.loaders:
                loader.finalize()
            raise

        for loader in self.loaders:
            loader.finalize()

        metrics.finish()
        self.audit_store.finish_run(
            run_id=self.run_id,
            status=run_status,
            metrics=metrics,
            error_message=error_message,
        )

        return metrics

    def _process_batch(
        self,
        batch: list[Record],
        metrics: PipelineMetrics,
        all_processed_records: list[Record],
    ) -> None:
        valid_records: list[Record] = []

        for record in batch:
            for validator in self.validators:
                validator.validate(record)

            if not record.is_valid:
                metrics.records_invalid += 1
                if self.error_strategy == ErrorStrategy.FAIL_FAST:
                    first_err = record.errors[0] if record.errors else "Validation failed"
                    raise PipelineError(f"Row {record.row_number} validation error: {first_err}")
                elif self.error_strategy == ErrorStrategy.QUARANTINE:
                    record.mark_quarantined()
                    metrics.records_quarantined += 1
                    self.audit_store.save_quarantined_record(
                        run_id=self.run_id,
                        row_number=record.row_number,
                        raw_data=record.raw_data,
                        errors=record.errors,
                    )
                elif self.error_strategy == ErrorStrategy.SKIP:
                    record.mark_skipped()
                    metrics.records_skipped += 1
            else:
                metrics.records_valid += 1
                valid_records.append(record)

        transformed_batch: list[Record] = []
        for record in valid_records:
            transformed = self.transformer_chain.transform(record)
            if transformed is None:
                metrics.records_skipped += 1
            else:
                metrics.records_transformed += 1
                transformed_batch.append(transformed)

        if not self.aggregator:
            for loader in self.loaders:
                loader.load(transformed_batch)
            metrics.records_loaded += len(transformed_batch)

        all_processed_records.extend(transformed_batch)
