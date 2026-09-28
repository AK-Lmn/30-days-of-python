from abc import ABC, abstractmethod
from pipeforge.models.record import Record


class BaseTransformer(ABC):
    @abstractmethod
    def transform(self, record: Record) -> Record | None:
        pass
