from typing import Any
from pydantic import BaseModel, ValidationError, create_model
from pipeforge.validators.base import BaseValidator
from pipeforge.models.record import Record


class SchemaValidator(BaseValidator):
    def __init__(self, model: type[BaseModel] | dict[str, Any]):
        if isinstance(model, dict):
            field_definitions: dict[str, Any] = {}
            for field_name, field_type in model.items():
                if isinstance(field_type, tuple):
                    field_definitions[field_name] = field_type
                else:
                    field_definitions[field_name] = (field_type, ...)
            self.model: type[BaseModel] = create_model("DynamicSchema", **field_definitions)
        else:
            self.model = model

    def validate(self, record: Record) -> Record:
        try:
            instance = self.model.model_validate(record.data)
            record.data = instance.model_dump()
            record.mark_valid()
        except ValidationError as err:
            for error in err.errors():
                loc = ".".join(str(x) for x in error.get("loc", []))
                msg = error.get("msg", "Validation error")
                field_str = f"'{loc}'" if loc else "root"
                record.add_error(f"Schema violation at {field_str}: {msg}")
        return record
