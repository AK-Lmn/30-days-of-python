import asyncio
import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone

from flagforge.core.errors import FlagNotFoundError, FlagAlreadyExistsError
from flagforge.models.flag import FlagCreate, FlagResponse, FlagUpdate
from flagforge.models.audit import AuditLogEntry, AuditAction


class InMemoryFlagRepository:
    def __init__(self, persistence_path: Optional[Path] = None):
        self._flags: dict[str, FlagResponse] = {}
        self._lock = asyncio.Lock()
        self._persistence_path = persistence_path
        if self._persistence_path and self._persistence_path.exists():
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        try:
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    flag = FlagResponse.model_validate(item)
                    self._flags[flag.key] = flag
        except Exception:
            pass

    def _save_to_disk(self) -> None:
        if not self._persistence_path:
            return
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persistence_path, "w", encoding="utf-8") as f:
            dumped = [flag.model_dump(mode="json") for flag in self._flags.values()]
            json.dump(dumped, f, indent=2)

    async def get(self, key: str) -> Optional[FlagResponse]:
        async with self._lock:
            return self._flags.get(key)

    async def list(
        self,
        offset: int = 0,
        limit: int = 50,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> tuple[list[FlagResponse], int]:
        async with self._lock:
            items = list(self._flags.values())

            if tag:
                normalized_tag = tag.strip().lower()
                items = [item for item in items if normalized_tag in item.tags]

            if search:
                query = search.strip().lower()
                items = [
                    item for item in items
                    if query in item.key.lower() or query in item.name.lower() or query in item.description.lower()
                ]

            if enabled is not None:
                items = [item for item in items if item.enabled == enabled]

            items.sort(key=lambda x: x.key)
            total = len(items)
            paginated = items[offset : offset + limit]
            return paginated, total

    async def create(self, flag_in: FlagCreate) -> FlagResponse:
        async with self._lock:
            if flag_in.key in self._flags:
                raise FlagAlreadyExistsError(flag_in.key)

            now = datetime.now(timezone.utc)
            flag = FlagResponse(
                key=flag_in.key,
                name=flag_in.name,
                description=flag_in.description,
                flag_type=flag_in.flag_type,
                enabled=flag_in.enabled,
                default_value=flag_in.default_value,
                rules=flag_in.rules,
                tags=flag_in.tags,
                created_at=now,
                updated_at=now,
                version=1,
            )
            self._flags[flag.key] = flag
            self._save_to_disk()
            return flag

    async def update(self, key: str, update_data: FlagUpdate) -> FlagResponse:
        async with self._lock:
            if key not in self._flags:
                raise FlagNotFoundError(key)

            current = self._flags[key]
            updated_dict = current.model_dump()

            if update_data.name is not None:
                updated_dict["name"] = update_data.name
            if update_data.description is not None:
                updated_dict["description"] = update_data.description
            if update_data.enabled is not None:
                updated_dict["enabled"] = update_data.enabled
            if update_data.default_value is not None:
                updated_dict["default_value"] = update_data.default_value
            if update_data.rules is not None:
                updated_dict["rules"] = [r.model_dump() for r in update_data.rules]
            if update_data.tags is not None:
                updated_dict["tags"] = update_data.tags

            updated_dict["updated_at"] = datetime.now(timezone.utc)
            updated_dict["version"] = current.version + 1

            updated_flag = FlagResponse.model_validate(updated_dict)
            self._flags[key] = updated_flag
            self._save_to_disk()
            return updated_flag

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key not in self._flags:
                raise FlagNotFoundError(key)
            del self._flags[key]
            self._save_to_disk()
            return True

    async def count_summary(self) -> tuple[int, int, int]:
        async with self._lock:
            total = len(self._flags)
            enabled = sum(1 for f in self._flags.values() if f.enabled)
            disabled = total - enabled
            return total, enabled, disabled


class InMemoryAuditRepository:
    def __init__(self):
        self._entries: list[AuditLogEntry] = []
        self._lock = asyncio.Lock()

    async def record(self, entry: AuditLogEntry) -> None:
        async with self._lock:
            self._entries.append(entry)

    async def list(
        self,
        flag_key: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLogEntry], int]:
        async with self._lock:
            filtered = self._entries
            if flag_key:
                filtered = [e for e in filtered if e.flag_key == flag_key]

            filtered.sort(key=lambda x: x.timestamp, reverse=True)
            total = len(filtered)
            paginated = filtered[offset : offset + limit]
            return paginated, total


class MetricsTracker:
    def __init__(self):
        self._total_evaluations: int = 0
        self._flag_evaluations: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def record_evaluation(self, flag_key: str) -> None:
        async with self._lock:
            self._total_evaluations += 1
            self._flag_evaluations[flag_key] = self._flag_evaluations.get(flag_key, 0) + 1

    async def get_metrics(self) -> tuple[int, dict[str, int]]:
        async with self._lock:
            return self._total_evaluations, dict(self._flag_evaluations)
