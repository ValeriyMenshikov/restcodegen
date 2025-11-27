import json
from pathlib import Path
from restcodegen.generator.parser import Parser


def test_parser_initialization(sample_openapi_spec: dict) -> None:
    """Test Parser initialization and parsing."""

    parser = Parser(sample_openapi_spec, "test_service")

    assert parser.service_name == "test_service"
    assert len(parser.operations) > 0
    assert "users" in parser.all_tags
    assert "posts" in parser.all_tags


def test_apis_property(sample_openapi_spec: dict) -> None:
    """Test the apis property returns correct tags."""

    # Test with no selected tags
    parser = Parser(sample_openapi_spec, "test_service")
    assert "users" in parser.apis
    assert "posts" in parser.apis

    # Test with selected tags
    parser = Parser(sample_openapi_spec, "test_service", selected_tags=["users"])
    assert "users" in parser.apis
    assert "posts" not in parser.apis

    # Test with non-existent tag
    parser = Parser(sample_openapi_spec, "test_service", selected_tags=["nonexistent"])
    assert "users" in parser.apis  # Should fall back to all tags
    assert "posts" in parser.apis



def test_handlers_by_tag(sample_openapi_spec: dict) -> None:
    """Test handlers_by_tag returns correct handlers."""

    parser = Parser(sample_openapi_spec, "test_service")

    # Check handlers for users tag
    users_handlers = parser.handlers_by_tag("users")
    assert len(users_handlers) == 2
    assert any(h.operation.operationId == "getUsers" for h in users_handlers)
    assert any(h.operation.operationId == "createUser" for h in users_handlers)

    # Check handlers for posts tag
    posts_handlers = parser.handlers_by_tag("posts")
    assert len(posts_handlers) == 1
    assert posts_handlers[0].operation.operationId == "getPosts"

    # Check handlers for non-existent tag
    nonexistent_handlers = parser.handlers_by_tag("nonexistent")
    assert len(nonexistent_handlers) == 0



def test_models_by_tag(sample_openapi_spec: dict) -> None:
    """Test models_by_tag returns correct models."""

    parser = Parser(sample_openapi_spec, "test_service")

    # Check models for users tag
    users_models = parser.models_by_tag("users")
    assert "User" in users_models
    assert "UserList" in users_models

    # Check models for posts tag
    posts_models = parser.models_by_tag("posts")
    assert "PostList" in posts_models



def test_request_models(sample_openapi_spec: dict) -> None:
    """Test request_models returns correct models."""

    parser = Parser(sample_openapi_spec, "test_service")

    request_models = parser.request_models()
    assert "User" in request_models



def test_response_models(sample_openapi_spec: dict) -> None:
    """Test response_models returns correct models."""

    parser = Parser(sample_openapi_spec, "test_service")

    response_models = parser.response_models()
    assert "User" in response_models
    assert "UserList" in response_models
    assert "PostList" in response_models


def test_parser_with_remote_petstore_spec() -> None:
    """Integration test against the public Petstore specification."""
    parser = Parser.from_source("https://petstore3.swagger.io/api/v3/openapi.json", "petstore")
    assert parser.service_name == "petstore"
    assert parser.openapi_version.startswith("3.")
    assert "pet" in parser.apis
    assert parser.handlers_by_tag("pet")
