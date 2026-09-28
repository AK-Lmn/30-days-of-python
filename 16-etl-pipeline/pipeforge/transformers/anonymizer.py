import hashlib
import re
from pipeforge.transformers.base import BaseTransformer
from pipeforge.models.record import Record


class FieldAnonymizer(BaseTransformer):
    def __init__(
        self,
        fields: list[str],
        strategy: str = "hash",
        salt: str = "",
        mask_char: str = "*",
    ):
        self.fields = fields
        self.strategy = strategy.lower()
        self.salt = salt
        self.mask_char = mask_char

    def _hash_val(self, val: str) -> str:
        salted = f"{self.salt}{val}"
        return hashlib.sha256(salted.encode("utf-8")).hexdigest()

    def _mask_email(self, val: str) -> str:
        if "@" not in val:
            return self.mask_char * len(val)
        username, domain = val.split("@", 1)
        if len(username) <= 2:
            masked_user = self.mask_char * len(username)
        else:
            masked_user = username[0] + (self.mask_char * (len(username) - 2)) + username[-1]
        return f"{masked_user}@{domain}"

    def _mask_phone(self, val: str) -> str:
        digits = re.sub(r"\D", "", val)
        if len(digits) <= 4:
            return self.mask_char * len(val)
        last4 = digits[-4:]
        return f"***-***-{last4}"

    def transform(self, record: Record) -> Record | None:
        for field in self.fields:
            if field in record.data and record.data[field] is not None:
                val_str = str(record.data[field])
                if self.strategy == "hash":
                    record.data[field] = self._hash_val(val_str)
                elif self.strategy == "mask_email":
                    record.data[field] = self._mask_email(val_str)
                elif self.strategy == "mask_phone":
                    record.data[field] = self._mask_phone(val_str)
                elif self.strategy == "redact":
                    record.data[field] = "[REDACTED]"
        return record
