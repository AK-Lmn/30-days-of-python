from typing import Optional

from autoflow.actions.base import BaseAction
from autoflow.actions.delay import DelayAction
from autoflow.actions.file_ops import FileAppendAction, FileWriteAction
from autoflow.actions.http import HttpAction
from autoflow.actions.notification import NotificationAction
from autoflow.actions.transform import TransformAction


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, BaseAction] = {}
        self.register_defaults()

    def register(self, action: BaseAction) -> None:
        self._actions[action.action_type] = action

    def get(self, action_type: str) -> Optional[BaseAction]:
        return self._actions.get(action_type)

    def list_actions(self) -> list[BaseAction]:
        return list(self._actions.values())

    def register_defaults(self) -> None:
        self.register(HttpAction())
        self.register(NotificationAction())
        self.register(TransformAction())
        self.register(FileWriteAction())
        self.register(FileAppendAction())
        self.register(DelayAction())


registry = ActionRegistry()
