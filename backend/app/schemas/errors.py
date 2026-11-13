from pydantic import BaseModel, JsonValue


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail | list[dict[str, JsonValue]]
