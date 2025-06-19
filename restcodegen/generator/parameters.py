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
    default: Any

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)
