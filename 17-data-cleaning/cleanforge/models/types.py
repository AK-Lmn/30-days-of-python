from enum import Enum


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    UUID = "uuid"
    EMPTY = "empty"


class CasingType(str, Enum):
    LOWER = "lower"
    UPPER = "upper"
    TITLE = "title"
    CAPITALIZE = "capitalize"
    SNAKE = "snake"
    CAMEL = "camel"
    KEBAB = "kebab"


class ImputeStrategy(str, Enum):
    CONSTANT = "constant"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    DROP_ROW = "drop_row"


class OutlierStrategy(str, Enum):
    CLIP = "clip"
    DROP = "drop"
    NULLIFY = "nullify"
    MEDIAN = "median"
    MEAN = "mean"


class OutlierMethod(str, Enum):
    IQR = "iqr"
    ZSCORE = "zscore"


class DuplicateKeep(str, Enum):
    FIRST = "first"
    LAST = "last"
    NONE = "none"
