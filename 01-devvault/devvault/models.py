from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

VALID_ITEM_TYPES = {"snippet", "command", "note", "url"}


@dataclass
class VaultItem:
    title: str
    item_type: str
    content: str
    id: Optional[int] = None
    language: Optional[str] = None
    description: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def __post_init__(self):
        self.item_type = self.item_type.strip().lower()
        if self.item_type not in VALID_ITEM_TYPES:
            raise ValueError(
                f"Invalid item type '{self.item_type}'. Must be one of: {', '.join(sorted(VALID_ITEM_TYPES))}"
            )
        if self.language:
            self.language = self.language.strip().lower()
        if self.description:
            self.description = self.description.strip()
        self.title = self.title.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "item_type": self.item_type,
            "content": self.content,
            "language": self.language,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: Any) -> "VaultItem":
        return cls(
            id=row["id"] if hasattr(row, "keys") else row[0],
            title=row["title"] if hasattr(row, "keys") else row[1],
            item_type=row["item_type"] if hasattr(row, "keys") else row[2],
            content=row["content"] if hasattr(row, "keys") else row[3],
            language=row["language"] if hasattr(row, "keys") else row[4],
            description=row["description"] if hasattr(row, "keys") else row[5],
            created_at=row["created_at"] if hasattr(row, "keys") else row[6],
            updated_at=row["updated_at"] if hasattr(row, "keys") else row[7],
        )
