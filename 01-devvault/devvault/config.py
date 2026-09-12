import os
from pathlib import Path
from typing import Optional

DEFAULT_VAULT_DIR = Path.home() / ".devvault"
DEFAULT_DB_FILE = DEFAULT_VAULT_DIR / "vault.db"


def get_db_path(override_path: Optional[str] = None) -> Path:
    if override_path:
        path = Path(override_path).expanduser().resolve()
    elif os.environ.get("DEVVAULT_DB"):
        path = Path(os.environ["DEVVAULT_DB"]).expanduser().resolve()
    else:
        path = DEFAULT_DB_FILE

    path.parent.mkdir(parents=True, exist_ok=True)
    return path
