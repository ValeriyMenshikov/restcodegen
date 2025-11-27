from pathlib import Path

import pytest

from restcodegen.generator.parser import Parser
from restcodegen.generator.codegen import RESTClientGenerator


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
def test_generate_creates_expected_files(tmp_output: Path, sample_openapi_spec: dict) -> None:
    parser = Parser(sample_openapi_spec, "Dummy")
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
