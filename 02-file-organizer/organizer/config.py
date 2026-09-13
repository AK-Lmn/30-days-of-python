import json
import os
from pathlib import Path
from typing import Any, Optional
import yaml
from organizer.models import CustomRule, OrganizerConfig

DEFAULT_CATEGORIES = {
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".heic", ".raw"
    ],
    "Documents": [
        ".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".tsv", ".epub"
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"
    ],
    "Video": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v"
    ],
    "Archives": [
        ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".iso"
    ],
    "Code": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".xml", ".sh", ".bat", ".ps1", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".sql", ".php", ".rb"
    ],
    "Executables": [
        ".exe", ".msi", ".dmg", ".pkg", ".appimage", ".deb", ".rpm"
    ],
    "Data": [
        ".sqlite", ".db", ".sqlite3", ".parquet", ".feather", ".hdf5", ".pkl"
    ],
}

DEFAULT_IGNORED_PATTERNS = [
    ".*",
    "desktop.ini",
    "thumbs.db",
    ".DS_Store",
]

DEFAULT_IGNORED_DIRECTORIES = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode",
]


def get_default_app_dir() -> Path:
    base = Path.home() / ".smart-organizer"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_history_db_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        db_path = Path(custom_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    env_path = os.environ.get("ORGANIZER_DB")
    if env_path:
        db_path = Path(env_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    return get_default_app_dir() / "history.db"


def load_config(config_path: Optional[Path] = None) -> OrganizerConfig:
    resolved_path: Optional[Path] = None
    if config_path and config_path.is_file():
        resolved_path = config_path
    else:
        local_yaml = Path("organizer.yaml")
        local_json = Path("organizer.json")
        global_yaml = get_default_app_dir() / "config.yaml"
        if local_yaml.is_file():
            resolved_path = local_yaml
        elif local_json.is_file():
            resolved_path = local_json
        elif global_yaml.is_file():
            resolved_path = global_yaml

    categories = {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}
    ignored_patterns = list(DEFAULT_IGNORED_PATTERNS)
    ignored_directories = list(DEFAULT_IGNORED_DIRECTORIES)
    rules: list[CustomRule] = []

    if resolved_path and resolved_path.is_file():
        content = resolved_path.read_text(encoding="utf-8")
        raw: dict[str, Any] = {}
        if resolved_path.suffix.lower() in [".yaml", ".yml"]:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                raw = parsed
        elif resolved_path.suffix.lower() == ".json":
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                raw = parsed

        if "categories" in raw and isinstance(raw["categories"], dict):
            for cat_name, exts in raw["categories"].items():
                if isinstance(exts, list):
                    normalized_exts = [
                        e.lower() if e.startswith(".") else f".{e.lower()}"
                        for e in exts
                        if isinstance(e, str)
                    ]
                    categories[cat_name] = normalized_exts

        if "ignored_patterns" in raw and isinstance(raw["ignored_patterns"], list):
            for pat in raw["ignored_patterns"]:
                if isinstance(pat, str) and pat not in ignored_patterns:
                    ignored_patterns.append(pat)

        if "ignored_directories" in raw and isinstance(raw["ignored_directories"], list):
            for dirname in raw["ignored_directories"]:
                if isinstance(dirname, str) and dirname not in ignored_directories:
                    ignored_directories.append(dirname)

        if "rules" in raw and isinstance(raw["rules"], list):
            for item in raw["rules"]:
                if isinstance(item, dict) and "name" in item and "folder" in item:
                    exts = item.get("extensions", [])
                    norm_exts = [
                        e.lower() if e.startswith(".") else f".{e.lower()}"
                        for e in exts
                        if isinstance(e, str)
                    ]
                    rules.append(
                        CustomRule(
                            name=str(item["name"]),
                            folder=str(item["folder"]),
                            extensions=norm_exts,
                            pattern=item.get("pattern"),
                            min_size=item.get("min_size"),
                            max_size=item.get("max_size"),
                        )
                    )

    return OrganizerConfig(
        categories=categories,
        rules=rules,
        ignored_patterns=ignored_patterns,
        ignored_directories=ignored_directories,
    )


def generate_starter_config() -> str:
    template = {
        "categories": {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
            "Documents": [".pdf", ".docx", ".txt", ".md", ".xlsx", ".pptx", ".csv"],
            "Audio": [".mp3", ".wav", ".flac"],
            "Video": [".mp4", ".mkv", ".mov"],
            "Archives": [".zip", ".tar.gz", ".7z", ".rar"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".json"],
        },
        "rules": [
            {
                "name": "Invoices",
                "folder": "Documents/Invoices",
                "pattern": "(?i)^inv.*\\.pdf$",
            },
            {
                "name": "Screenshots",
                "folder": "Images/Screenshots",
                "pattern": "(?i)^screenshot.*\\.(png|jpg)$",
            },
        ],
        "ignored_patterns": [
            ".*",
            "desktop.ini",
            "thumbs.db",
        ],
        "ignored_directories": [
            ".git",
            ".venv",
            "node_modules",
        ],
    }
    return yaml.dump(template, sort_keys=False, default_flow_style=False)
