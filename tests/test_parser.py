import pytest
from unittest.mock import patch, MagicMock

from restcodegen.generator.parser import Parser


@pytest.fixture
def sample_openapi_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0", "description": "API for testing"},
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
                },
                "post": {
                    "operationId": "createUser",
                    "tags": ["users"],
                    "summary": "Create user",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}},
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                        }
                    },
                },
            },
            "/posts": {
                "get": {
                    "operationId": "getPosts",
                    "tags": ["posts"],
                    "summary": "Get posts",
                    "parameters": [{"name": "userId", "in": "query", "required": False, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PostList"}}},
                        }
                    },
                }
            },
        },
    }


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_parser_initialization(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test Parser initialization and parsing."""
    # Setup mock for spec loader
    mock_spec_loader.return_value = sample_openapi_spec

    # Initialize parser
    parser = Parser("http://example.com/openapi.json", "test_service")

    # Check basic properties
    assert parser.service_name == "test_service"
    assert parser.client_type == "http"
    assert len(parser.all_tags) > 0
    assert "users" in parser.all_tags
    assert "posts" in parser.all_tags


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_apis_property(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test the apis property returns correct tags."""
    mock_spec_loader.return_value = sample_openapi_spec

    # Test with no selected tags
    parser = Parser("http://example.com/openapi.json", "test_service")
    assert "users" in parser.apis
    assert "posts" in parser.apis

    # Test with selected tags
    parser = Parser("http://example.com/openapi.json", "test_service", selected_tags=["users"])
    assert "users" in parser.apis
    assert "posts" not in parser.apis

    # Test with non-existent tag
    parser = Parser("http://example.com/openapi.json", "test_service", selected_tags=["nonexistent"])
    assert "users" in parser.apis  # Should fall back to all tags
    assert "posts" in parser.apis


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_handlers_by_tag(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test handlers_by_tag returns correct handlers."""
    mock_spec_loader.return_value = sample_openapi_spec

    parser = Parser("http://example.com/openapi.json", "test_service")

    # Check handlers for users tag
    users_handlers = parser.handlers_by_tag("users")
    assert len(users_handlers) == 2
    assert any(h.operation_id == "getUsers" for h in users_handlers)
    assert any(h.operation_id == "createUser" for h in users_handlers)

    # Check handlers for posts tag
    posts_handlers = parser.handlers_by_tag("posts")
    assert len(posts_handlers) == 1
    assert posts_handlers[0].operation_id == "getPosts"

    # Check handlers for non-existent tag
    nonexistent_handlers = parser.handlers_by_tag("nonexistent")
    assert len(nonexistent_handlers) == 0


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_models_by_tag(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test models_by_tag returns correct models."""
    mock_spec_loader.return_value = sample_openapi_spec

    parser = Parser("http://example.com/openapi.json", "test_service")

    # Check models for users tag
    users_models = parser.models_by_tag("users")
    assert "User" in users_models
    assert "UserList" in users_models

    # Check models for posts tag
    posts_models = parser.models_by_tag("posts")
    assert "PostList" in posts_models


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_request_models(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test request_models returns correct models."""
    mock_spec_loader.return_value = sample_openapi_spec

    parser = Parser("http://example.com/openapi.json", "test_service")

    request_models = parser.request_models()
    assert "User" in request_models


@patch("restcodegen.generator.spec_loader.SpecLoader.open")
def test_response_models(mock_spec_loader: MagicMock, sample_openapi_spec: dict) -> None:
    """Test response_models returns correct models."""
    mock_spec_loader.return_value = sample_openapi_spec

    parser = Parser("http://example.com/openapi.json", "test_service")

    response_models = parser.response_models()
    assert "User" in response_models
    assert "UserList" in response_models
    assert "PostList" in response_models
