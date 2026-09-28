from abc import ABC, abstractmethod
from typing import Any
from pipeforge.models.record import Record


class BaseLoader(ABC):
    def initialize(self) -> None:
        pass

    @abstractmethod
    def load(self, records: list[Record]) -> int:
        pass

    def finalize(self) -> None:
        pass

    def get_metadata(self) -> dict[str, Any]:
        return {"loader": self.__class__.__name__}
