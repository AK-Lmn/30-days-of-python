import re
from abc import ABC, abstractmethod
from typing import Any
from pipeforge.validators.base import BaseValidator
from pipeforge.models.record import Record


class FieldRule(ABC):
    def __init__(self, field_name: str):
        self.field_name = field_name

    @abstractmethod
    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        pass


class NotEmptyRule(FieldRule):
    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        if value is None:
            return False, f"Field '{self.field_name}' must not be null"
        if isinstance(value, str) and not value.strip():
            return False, f"Field '{self.field_name}' must not be empty"
        if isinstance(value, (list, dict, set)) and len(value) == 0:
            return False, f"Field '{self.field_name}' must not be empty"
        return True, None


class RangeRule(FieldRule):
    def __init__(
        self,
        field_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ):
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value

    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        if value is None:
            return True, None
        try:
            num = float(value)
        except (ValueError, TypeError):
            return False, f"Field '{self.field_name}' must be numeric"

        if self.min_value is not None and num < self.min_value:
            return False, f"Field '{self.field_name}' must be >= {self.min_value} (got {num})"
        if self.max_value is not None and num > self.max_value:
            return False, f"Field '{self.field_name}' must be <= {self.max_value} (got {num})"
        return True, None


class RegexRule(FieldRule):
    def __init__(self, field_name: str, pattern: str, message: str | None = None):
        super().__init__(field_name)
        self.pattern = pattern
        self.regex = re.compile(pattern)
        self.message = message

    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        if value is None:
            return True, None
        val_str = str(value)
        if not self.regex.search(val_str):
            msg = self.message or f"Field '{self.field_name}' does not match pattern {self.pattern}"
            return False, msg
        return True, None


class EmailRule(FieldRule):
    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, field_name: str):
        super().__init__(field_name)

    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        if value is None:
            return True, None
        val_str = str(value).strip()
        if not self.EMAIL_REGEX.match(val_str):
            return False, f"Field '{self.field_name}' is not a valid email address: {value}"
        return True, None


class InListRule(FieldRule):
    def __init__(self, field_name: str, allowed_values: list[Any]):
        super().__init__(field_name)
        self.allowed_values = allowed_values

    def evaluate(self, value: Any) -> tuple[bool, str | None]:
        if value is None:
            return True, None
        if value not in self.allowed_values:
            return False, f"Field '{self.field_name}' must be one of {self.allowed_values} (got {value})"
        return True, None


class RuleValidator(BaseValidator):
    def __init__(self, rules: list[FieldRule] | None = None):
        self.rules = rules or []

    def add_rule(self, rule: FieldRule) -> "RuleValidator":
        self.rules.append(rule)
        return self

    def validate(self, record: Record) -> Record:
        for rule in self.rules:
            val = record.data.get(rule.field_name)
            ok, err = rule.evaluate(val)
            if not ok and err:
                record.add_error(err)
        if record.is_valid:
            record.mark_valid()
        return record
