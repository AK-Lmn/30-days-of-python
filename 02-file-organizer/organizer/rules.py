import fnmatch
import re
from pathlib import Path
from organizer.models import (
    CustomRule,
    FileItem,
    OrganizerConfig,
    OrganizeStrategy,
)


def is_ignored_file(name: str, ignored_patterns: list[str]) -> bool:
    for pattern in ignored_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if pattern.startswith(".*") and name.startswith("."):
            return True
    return False


def is_ignored_dir(name: str, ignored_directories: list[str]) -> bool:
    lower_name = name.lower()
    for ignored in ignored_directories:
        if lower_name == ignored.lower() or fnmatch.fnmatch(lower_name, ignored.lower()):
            return True
    return False


def match_custom_rule(item: FileItem, rules: list[CustomRule]) -> str | None:
    for rule in rules:
        if rule.extensions:
            file_ext = item.extension.lower()
            if not any(file_ext == e.lower() for e in rule.extensions):
                continue

        if rule.pattern:
            if not re.search(rule.pattern, item.name):
                continue

        if rule.min_size is not None and item.size < rule.min_size:
            continue

        if rule.max_size is not None and item.size > rule.max_size:
            continue

        return rule.folder
    return None


def get_category_for_extension(ext: str, categories: dict[str, list[str]]) -> str:
    normalized_ext = ext.lower()
    for category_name, extensions in categories.items():
        if normalized_ext in [e.lower() for e in extensions]:
            return category_name
    return "Other"


def get_size_tier(size_bytes: int) -> str:
    one_mb = 1024 * 1024
    one_gb = 1024 * one_mb
    if size_bytes < one_mb:
        return "Tiny (<1MB)"
    if size_bytes < 10 * one_mb:
        return "Small (1-10MB)"
    if size_bytes < 100 * one_mb:
        return "Medium (10-100MB)"
    if size_bytes < one_gb:
        return "Large (100MB-1GB)"
    return "Huge (>1GB)"


def get_date_folder(item: FileItem) -> str:
    year = item.modified_at.strftime("%Y")
    month = item.modified_at.strftime("%Y-%m")
    return f"{year}/{month}"


def resolve_relative_destination(
    item: FileItem,
    strategy: OrganizeStrategy,
    config: OrganizerConfig,
    date_subfolders: bool = False,
) -> tuple[str, Path]:
    custom_folder = match_custom_rule(item, config.rules)
    if custom_folder:
        target_dir = Path(custom_folder)
        if date_subfolders:
            target_dir = target_dir / get_date_folder(item)
        return "Custom", target_dir / item.name

    if strategy == OrganizeStrategy.CATEGORY:
        category = get_category_for_extension(item.extension, config.categories)
        target_dir = Path(category)
        if date_subfolders:
            target_dir = target_dir / get_date_folder(item)
        return category, target_dir / item.name

    if strategy == OrganizeStrategy.EXTENSION:
        ext_clean = item.extension.lstrip(".").upper() if item.extension else "NO_EXT"
        target_dir = Path(ext_clean)
        if date_subfolders:
            target_dir = target_dir / get_date_folder(item)
        return ext_clean, target_dir / item.name

    if strategy == OrganizeStrategy.DATE:
        date_folder = get_date_folder(item)
        target_dir = Path(date_folder)
        return date_folder, target_dir / item.name

    if strategy == OrganizeStrategy.SIZE:
        size_tier = get_size_tier(item.size)
        target_dir = Path(size_tier)
        if date_subfolders:
            target_dir = target_dir / get_date_folder(item)
        return size_tier, target_dir / item.name

    return "Other", Path("Other") / item.name
