import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from restcodegen.generator.spec_loader import SpecLoader


@pytest.fixture
def sample_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


def test_init() -> None:
    """Test initialization of SpecLoader."""
    loader = SpecLoader("http://example.com/openapi.json", "test_service")
    assert loader.spec_path == "http://example.com/openapi.json"
    assert loader.service_name == "test_service"
    assert loader.cache_spec_path.name == "test_service.json"


def test_open_from_url() -> None:
    loader = SpecLoader(
        "https://petstore3.swagger.io/api/v3/openapi.json", "test_service"
    )
    assert isinstance(loader.open(), dict)


def test_open_from_file() -> None:
    loader = SpecLoader("tests/minimal_swagger.json", "test_service")
    assert isinstance(loader.open(), dict)


@pytest.mark.skip("TODO")
def test_open_from_cache() -> None: ...


def test_open_all_sources_fail() -> None:
    with pytest.raises(FileNotFoundError):
        loader = SpecLoader("not_available.json", "not_available")
        loader.open()
