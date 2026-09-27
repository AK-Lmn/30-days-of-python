from pathlib import Path
from typing import Any

from autoflow.actions.base import BaseAction
from autoflow.models.enums import ActionType


class FileWriteAction(BaseAction):
    action_type = ActionType.FILE_WRITE.value
    display_name = "Write File"
    description = "Writes formatted text or data to a specified local file"
    parameters_schema = {
        "path": {"type": "string", "required": True},
        "content": {"type": "string", "required": True},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        file_path_str = config.get("path")
        if not file_path_str:
            raise ValueError("File write requires 'path'")
        content = config.get("content", "")

        path = Path(file_path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return {
            "path": str(path.resolve()),
            "bytes_written": len(content.encode("utf-8")),
        }


class FileAppendAction(BaseAction):
    action_type = ActionType.FILE_APPEND.value
    display_name = "Append File"
    description = "Appends formatted text or data to a specified local file"
    parameters_schema = {
        "path": {"type": "string", "required": True},
        "content": {"type": "string", "required": True},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        file_path_str = config.get("path")
        if not file_path_str:
            raise ValueError("File append requires 'path'")
        content = config.get("content", "")

        path = Path(file_path_str)
        path.parent.mkdir(parents=True, exist_ok=True)

        prefix = ""
        if path.exists() and path.stat().st_size > 0:
            existing = path.read_text(encoding="utf-8")
            if not existing.endswith("\n"):
                prefix = "\n"

        to_write = prefix + content + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(to_write)

        return {
            "path": str(path.resolve()),
            "bytes_appended": len(to_write.encode("utf-8")),
        }
