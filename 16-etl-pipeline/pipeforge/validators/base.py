from abc import ABC, abstractmethod
from pipeforge.models.record import Record


class BaseValidator(ABC):
    @abstractmethod
    def validate(self, record: Record) -> Record:
        pass
