from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"


class BaseParameter(BaseModel):
    name: str
    description: str
    type: str = Field(..., alias="type_")
    required: bool
    default: Any | None = None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class Handler(BaseModel):
    path: str = Field(...)
    method: str = Field(...)
    tags: list = Field(...)
    summary: str | None = Field(None)
    operation_id: str | None = Field(None)
    path_parameters: list[BaseParameter] | None = Field(None)
    query_parameters: list[BaseParameter] | None = Field(None)
    headers: list[BaseParameter] | None = Field(None)
    request_body: str | None = Field(None)
    responses: dict | None = Field(None)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class OpenApiSpec(BaseModel):
    service_name: str = Field(...)
    version: str = Field(...)
    title: str = Field(...)
    description: str = Field(...)
    openapi_version: str = Field(...)
    handlers: list[Handler]
    request_models: set[str] = set()
    response_models: set[str] = set()
    api_tags: set[str] = set()
    all_tags: set[str] = set()
