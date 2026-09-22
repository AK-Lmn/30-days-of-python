from typing import Protocol, Optional
from flagforge.models.flag import FlagCreate, FlagResponse, FlagUpdate
from flagforge.models.audit import AuditLogEntry


class FlagRepository(Protocol):
    async def get(self, key: str) -> Optional[FlagResponse]:
        ...

    async def list(
        self,
        offset: int = 0,
        limit: int = 50,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> tuple[list[FlagResponse], int]:
        ...

    async def create(self, flag: FlagCreate) -> FlagResponse:
        ...

    async def update(self, key: str, update_data: FlagUpdate) -> FlagResponse:
        ...

    async def delete(self, key: str) -> bool:
        ...

    async def count_summary(self) -> tuple[int, int, int]:
        ...


class AuditRepository(Protocol):
    async def record(self, entry: AuditLogEntry) -> None:
        ...

    async def list(
        self,
        flag_key: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLogEntry], int]:
        ...
