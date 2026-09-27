from abc import ABC, abstractmethod
from typing import Any


class BaseAction(ABC):
    action_type: str
    display_name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        pass
