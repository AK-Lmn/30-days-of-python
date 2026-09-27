from enum import StrEnum


class TriggerType(StrEnum):
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionType(StrEnum):
    HTTP_REQUEST = "http_request"
    NOTIFICATION = "notification"
    TRANSFORM = "transform"
    FILE_WRITE = "file_write"
    FILE_APPEND = "file_append"
    DELAY = "delay"


class ComparisonOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    MATCHES_REGEX = "matches_regex"
