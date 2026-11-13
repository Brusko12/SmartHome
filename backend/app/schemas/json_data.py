from typing import Annotated

from pydantic import AfterValidator, ConfigDict, Field, JsonValue, TypeAdapter
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

# Strict JSON validation is shared by all ORM writes. Device-specific validation
# also runs in adapters; rule semantics will be added with the automation service.
JsonObject = dict[str, JsonValue]
config = ConfigDict(strict=True, allow_inf_nan=False)


class ValidatedJSON(TypeDecorator):
    impl = JSON
    cache_ok = True
    schema = JsonObject

    def __init__(self, none_as_null: bool = False):
        super().__init__(none_as_null=none_as_null)
        self.adapter = TypeAdapter(self.schema, config=config)

    def process_bind_param(self, value, dialect):
        if value is None and self.impl.none_as_null:
            return None
        return self.adapter.validate_python(value)


class ObjectJSON(ValidatedJSON):
    cache_ok = True


class ObjectsJSON(ValidatedJSON):
    cache_ok = True
    schema = list[JsonObject]


class ActionsJSON(ObjectsJSON):
    """A JSON array preserves action execution order."""

    cache_ok = True


Weekday = Annotated[int, Field(ge=0, le=6)]


def unique_sorted(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise ValueError("Weekdays must not repeat")
    return sorted(values)


class WeekdaysJSON(ValidatedJSON):
    cache_ok = True
    schema = Annotated[list[Weekday], Field(min_length=1), AfterValidator(unique_sorted)]
