from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ConflictResolution(str, Enum):
    RENAME = "rename"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    HASH_CHECK = "hash"


class OrganizeMode(str, Enum):
    MOVE = "move"
    COPY = "copy"


class OrganizeStrategy(str, Enum):
    CATEGORY = "category"
    EXTENSION = "extension"
    DATE = "date"
    SIZE = "size"


@dataclass
class FileItem:
    path: Path
    name: str
    extension: str
    size: int
    modified_at: datetime
    created_at: datetime


@dataclass
class OrganizeAction:
    source_path: Path
    destination_path: Path
    category: str
    action_type: str
    size: int
    checksum: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class OrganizeResult:
    session_id: Optional[int]
    total_files_scanned: int
    actions: list[OrganizeAction] = field(default_factory=list)
    skipped_count: int = 0
    moved_count: int = 0
    copied_count: int = 0
    bytes_processed: int = 0


@dataclass
class UndoAction:
    original_path: Path
    current_path: Path
    action_type: str


@dataclass
class UndoResult:
    session_id: int
    restored_count: int
    failed_count: int
    cleaned_directories: list[Path] = field(default_factory=list)


@dataclass
class DuplicateGroup:
    size: int
    checksum: str
    original: Path
    duplicates: list[Path] = field(default_factory=list)


@dataclass
class CustomRule:
    name: str
    folder: str
    extensions: list[str] = field(default_factory=list)
    pattern: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None


@dataclass
class OrganizerConfig:
    categories: dict[str, list[str]] = field(default_factory=dict)
    rules: list[CustomRule] = field(default_factory=list)
    ignored_patterns: list[str] = field(default_factory=list)
    ignored_directories: list[str] = field(default_factory=list)
