from typing import Any, Optional


class FlagForgeError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class FlagNotFoundError(FlagForgeError):
    def __init__(self, flag_key: str):
        super().__init__(
            message=f"Feature flag with key '{flag_key}' does not exist",
            code="FLAG_NOT_FOUND",
            details={"flag_key": flag_key},
        )


class FlagAlreadyExistsError(FlagForgeError):
    def __init__(self, flag_key: str):
        super().__init__(
            message=f"Feature flag with key '{flag_key}' already exists",
            code="FLAG_ALREADY_EXISTS",
            details={"flag_key": flag_key},
        )


class InvalidRuleError(FlagForgeError):
    def __init__(self, reason: str, rule_id: Optional[str] = None):
        super().__init__(
            message=f"Invalid targeting rule configuration: {reason}",
            code="INVALID_RULE",
            details={"reason": reason, "rule_id": rule_id} if rule_id else {"reason": reason},
        )


class EvaluationError(FlagForgeError):
    def __init__(self, flag_key: str, reason: str):
        super().__init__(
            message=f"Evaluation failed for flag '{flag_key}': {reason}",
            code="EVALUATION_FAILED",
            details={"flag_key": flag_key, "reason": reason},
        )
