from pipeforge.transformers.base import BaseTransformer
from pipeforge.models.record import Record


class TransformerChain(BaseTransformer):
    def __init__(self, transformers: list[BaseTransformer] | None = None):
        self.transformers = transformers or []

    def add(self, transformer: BaseTransformer) -> "TransformerChain":
        self.transformers.append(transformer)
        return self

    def transform(self, record: Record) -> Record | None:
        current: Record | None = record
        for transformer in self.transformers:
            if current is None:
                return None
            current = transformer.transform(current)
        if current is not None:
            current.mark_transformed()
        return current
