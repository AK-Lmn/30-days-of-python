from enum import Enum


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RecordStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    VALID = "VALID"
    INVALID = "INVALID"
    TRANSFORMED = "TRANSFORMED"
    LOADED = "LOADED"
    QUARANTINED = "QUARANTINED"
    SKIPPED = "SKIPPED"


class LoadMode(str, Enum):
    APPEND = "APPEND"
    REPLACE = "REPLACE"
    UPSERT = "UPSERT"


class ErrorStrategy(str, Enum):
    FAIL_FAST = "FAIL_FAST"
    QUARANTINE = "QUARANTINE"
    SKIP = "SKIP"


class ExtractorType(str, Enum):
    CSV = "CSV"
    JSON = "JSON"
    JSONL = "JSONL"
    API = "API"
    SQL = "SQL"
