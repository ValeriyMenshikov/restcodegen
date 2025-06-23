import json
import pytest

from restcodegen.generator.spec_patcher import SpecPatcher


@pytest.fixture
def simple_swagger_schema() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/posts": {
                "post": {
                    "operationId": "create_post",
                    "tags": ["posts"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "content": {"type": "string"},
                                    },
                                    "required": ["title", "content"],
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "title": {"type": "string"},
                                            "content": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }


@pytest.fixture
def schema_with_dots() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "User.Profile": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                }
            }
        },
        "paths": {
            "/users": {
                "get": {
                    "operationId": "get_users",
                    "tags": ["users.management"],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User.Profile"
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }


@pytest.fixture
def schema_with_nested_objects() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "operationId": "create_user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "address": {
                                            "type": "object",
                                            "properties": {
                                                "street": {"type": "string"},
                                                "city": {"type": "string"},
                                                "country": {"type": "string"},
                                            },
                                        },
                                        "contacts": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "type": {"type": "string"},
                                                    "value": {"type": "string"},
                                                },
                                            },
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


@pytest.fixture
def schema_with_combined_schemas() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/products": {
                "post": {
                    "operationId": "create_product",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string", "enum": ["physical"]},
                                                "weight": {"type": "number"},
                                                "dimensions": {
                                                    "type": "object",
                                                    "properties": {
                                                        "length": {"type": "number"},
                                                        "width": {"type": "number"},
                                                        "height": {"type": "number"},
                                                    },
                                                },
                                            },
                                        },
                                        {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string", "enum": ["digital"]},
                                                "fileSize": {"type": "number"},
                                                "format": {"type": "string"},
                                            },
                                        },
                                    ]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


def test_extract_inline_schemas(simple_swagger_schema: dict) -> None:
    """Test that inline schemas are extracted to components/schemas."""
    patcher = SpecPatcher()
    patched = patcher.patch(simple_swagger_schema)
    
    assert "components" in patched
    assert "schemas" in patched["components"]
    
    assert "create_post_request_body" in patched["components"]["schemas"]
    assert "create_post_response_201" in patched["components"]["schemas"]
    
    request_schema = patched["paths"]["/posts"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert "$ref" in request_schema
    assert request_schema["$ref"] == "#/components/schemas/create_post_request_body"
    
    response_schema = patched["paths"]["/posts"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]
    assert "$ref" in response_schema
    assert response_schema["$ref"] == "#/components/schemas/create_post_response_201"


def test_replace_dots_in_schema_names(schema_with_dots: dict) -> None:
    """Test that dots in schema names are replaced."""
    patcher = SpecPatcher()
    patched = patcher.patch(schema_with_dots)
    
    assert "User.Profile" not in patched["components"]["schemas"]
    assert "UserProfile" in patched["components"]["schemas"]
    
    ref = patched["paths"]["/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert "User.Profile" not in ref
    assert "UserProfile" in ref
    
    assert "users.management" not in patched["paths"]["/users"]["get"]["tags"]
    assert "usersmanagement" in patched["paths"]["/users"]["get"]["tags"]


def test_extract_nested_objects(schema_with_nested_objects: dict) -> None:
    """Test that nested objects are extracted to components/schemas."""
    patcher = SpecPatcher()
    patched = patcher.patch(schema_with_nested_objects)
    
    schemas = patched["components"]["schemas"]
    assert "create_user_request_body" in schemas
    assert "create_user_request_body_address" in schemas
    assert "create_user_request_body_contacts_item" in schemas
    
    address_schema = schemas["create_user_request_body_address"]
    assert address_schema["type"] == "object"
    assert "street" in address_schema["properties"]
    assert "city" in address_schema["properties"]
    
    contacts_schema = schemas["create_user_request_body"]["properties"]["contacts"]
    assert contacts_schema["type"] == "array"
    assert "$ref" in contacts_schema["items"]
    assert contacts_schema["items"]["$ref"] == "#/components/schemas/create_user_request_body_contacts_item"


def test_extract_combined_schemas(schema_with_combined_schemas: dict) -> None:
    """Test that combined schemas (oneOf, anyOf, allOf) are extracted."""
    patcher = SpecPatcher()
    patched = patcher.patch(schema_with_combined_schemas)
    
    schemas = patched["components"]["schemas"]
    assert "create_product_request_body" in schemas
    assert "create_product_request_body_oneOf_0" in schemas
    assert "create_product_request_body_oneOf_1" in schemas
    
    assert "create_product_request_body_oneOf_0_dimensions" in schemas
    
    oneof_schema = schemas["create_product_request_body"]["oneOf"]
    assert len(oneof_schema) == 2
    assert "$ref" in oneof_schema[0]
    assert "$ref" in oneof_schema[1]
    assert oneof_schema[0]["$ref"] == "#/components/schemas/create_product_request_body_oneOf_0"
    assert oneof_schema[1]["$ref"] == "#/components/schemas/create_product_request_body_oneOf_1"


def test_idempotent_patching(simple_swagger_schema: dict) -> None:
    """Test that patching an already patched schema doesn't change it further."""
    patcher = SpecPatcher()
    patched_once = patcher.patch(simple_swagger_schema)
    patched_twice = patcher.patch(patched_once)
    
    json_once = json.dumps(patched_once, sort_keys=True)
    json_twice = json.dumps(patched_twice, sort_keys=True)
    
    assert json_once == json_twice
