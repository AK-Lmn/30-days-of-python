from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any
from pipeforge.models.record import Record


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self) -> Generator[Record, None, None]:
        pass

    def get_metadata(self) -> dict[str, Any]:
        return {"extractor": self.__class__.__name__}

    def get_total_count(self) -> int | None:
        return None
