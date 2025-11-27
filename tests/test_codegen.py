from pathlib import Path

import pytest

from restcodegen.generator.parser import Parser
from restcodegen.generator.codegen import RESTClientGenerator
from restcodegen.generator.parser.types import BaseParameter
from restcodegen.generator.parser import Handler


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture()
def sample_openapi_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Dummy",
            "version": "1.0.0",
            "description": "Test spec",
        },
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "tags": ["users"],
                    "summary": "Get users",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserList"}}},
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],
                },
                "UserList": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/User"},
                },
            }
        },
    }


class DummyParser(Parser):
    def __init__(self, spec: dict) -> None:  # pragma: no cover - used only in tests
        self.openapi_spec = spec

    @property
    def apis(self) -> list[str]:  # type: ignore[override]
        return list(
            {
                tag
                for handler in self.openapi_spec.get("paths", {}).values()
                for tag in handler.get("get", {}).get("tags", [])
            }
        )

    @property
    def service_name(self) -> str:
        return self.openapi_spec.get("info", {}).get("title", "DummyService")

    def handlers_by_tag(self, tag: str) -> list[Handler]:  # type: ignore[override]
        handler = Handler(
            path="/users",
            method="get",
            tags=[tag],
            summary="Get users",
            operation_id="getUsers",
            path_parameters=[],
            query_parameters=[
                BaseParameter(
                    name="userId",
                    type_="int",
                    description="User ID",
                    required=False,
                    default=None,
                )
            ],
            headers=[],
            request_body=None,
            responses={"200": "UserList"},
        )
        return [handler]

    def models_by_tag(self, tag: str) -> list[str]:  # type: ignore[override]
        return ["User", "UserList"]


def test_generate_creates_expected_files(tmp_output: Path, sample_openapi_spec: dict) -> None:
    parser = DummyParser(sample_openapi_spec)
    generator = RESTClientGenerator(
        parser,
        templates_dir=str(Path(__file__).parent.parent / "restcodegen" / "templates"),
        base_path=tmp_output,
    )

    generator.generate()

    root = tmp_output / "dummy"
    assert (root / "__init__.py").exists()
    assert (root / "apis" / "__init__.py").exists()
    assert (root / "apis" / "users_api.py").exists()
    assert (root / "models" / "__init__.py").exists()
    assert (root / "models" / "api_models.py").exists()
