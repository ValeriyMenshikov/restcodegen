"""
OpenAPI specification parser for REST code generation.
"""
import json
import re
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    TypedDict,
)

import httpx
from pydantic import BaseModel, \
    Field, \
    HttpUrl

from restcodegen.generator.log import LOGGER
from restcodegen.generator.utils import name_to_snake, \
    snake_to_camel, \
    rename_python_builtins, \
    NamingUtils

class ParamType(str, Enum):
    """Parameter types in OpenAPI spec."""
    HEADER = "header"
    PATH = "path"
    QUERY = "query"
    BODY = "body"


# Type mapping from OpenAPI types to Python types
TYPE_MAP: dict[str, str] = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "boolean": "bool",
    "array": "list",
    "anyof": "str",
    "none": "Any",
}

# Default values for header parameters
DEFAULT_HEADER_VALUE_MAP: dict[str, Any] = {
    "int": 0,
    "float": 0.0,
    "str": "",
    "bool": True
}


class ParameterDict(TypedDict, total=False):
    """Type definition for parameter dictionaries."""
    name: str
    type: str
    description: str
    required: bool
    default: Any


class Handler(BaseModel):
    """Handler model representing an API endpoint."""
    path: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    tags: list[str] = Field(..., description="API tags")
    summary: str | None = Field(None, description="Endpoint summary")
    operation_id: str | None = Field(None, description="Operation ID")
    path_parameters: list[dict[str, Any]] | None = Field(None, description="Path parameters")
    query_parameters: list[dict[str, Any]] | None = Field(None, description="Query parameters")
    headers: list[dict[str, Any]] | None = Field(None, description="Header parameters")
    request_body: str | None = Field(None, description="Request body model name")
    responses: dict[str, str] | None = Field(None, description="Response models by status code")

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute by name with default fallback."""
        return getattr(self, key, default)


class OpenAPISpec:
    """
    OpenAPI specification parser that loads and processes OpenAPI/Swagger specifications.
    Supports both OpenAPI 3.x and Swagger 2.x formats.
    """
    BASE_PATH = Path.cwd() / "clients" / "http"
    EXCLUDED_PARAMS = ["x-o3-app-name"]

    def __init__(
            self,
            openapi_spec: str | HttpUrl,
            service_name: str,
            api_tags: list[str] | None = None,
    ) -> None:
        """
        Initialize OpenAPI specification parser.

        Args:
            openapi_spec: Path or URL to OpenAPI specification
            service_name: Service name
            api_tags: List of API tags to filter by
        """
        self.spec_path = str(openapi_spec)
        self.service_name = service_name
        self.cache_spec_dir = self._ensure_cache_dir()
        self.cache_spec_path = self.cache_spec_dir / f"{name_to_snake(self.service_name)}.json"

        # Parse OpenAPI spec
        self.openapi_spec: dict[str, Any] = self._load_spec()
        self.version: str = ""
        self.description: str = ""
        self.openapi_version: str = ""

        # Containers for parsed data
        self.handlers: [Handler] = []
        self.request_models: set[str] = set()
        self.response_models: set[str] = set()
        self.api_tags: set[str] = set(api_tags or [])
        self.all_tags: set[str] = set()

        # Process the specification
        self.parse_openapi_spec()

    def _ensure_cache_dir(self) -> Path:
        """Ensure cache directory exists and return its path."""
        cache_dir = self.BASE_PATH / "schemas"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def apis(self) -> set[str]:
        """
        Get filtered API tags based on provided api_tags.

        Returns:
            Set of API tags to process
        """
        result_tags = set()

        # Filter tags that exist in the spec
        for tag in self.api_tags:
            if tag not in self.all_tags:
                LOGGER.warning(f"Tag {tag} not found in OpenAPI spec")
            else:
                result_tags.add(tag)

        # Fallback to all tags if no valid tags found
        if not result_tags:
            if self.api_tags:
                LOGGER.warning("Tags not found in OpenAPI spec, using default tags")
            return self.all_tags

        return result_tags

    @property
    def client_type(self) -> str:
        """Get client type."""
        return "http"

    @staticmethod
    def _patch(swagger_scheme: dict[str, Any]) -> dict[str, Any]:
        """
        Patch swagger JSON to handle schemas with dots in their names.

        Args:
            swagger_scheme: Original swagger/OpenAPI JSON

        Returns:
            Patched swagger/OpenAPI JSON
        """
        json_content = json.dumps(swagger_scheme)

        # Find schemas that need patching (containing dots)
        schemas = swagger_scheme.get("components", {}).get(
            "schemas", {}
        ) or swagger_scheme.get("definitions", {})
        schemas_to_patch = [schema for schema in schemas if "." in schema]

        # Find tags with dots in paths
        for _, methods in swagger_scheme.get("paths", {}).items():
            for _, method in methods.items():
                for tag in method.get("tags", []):
                    if "." in tag:
                        schemas_to_patch.append(tag)

        # Replace dots in schema references
        for schema in schemas_to_patch:
            for text in [f'/{schema}"', f'"{schema}"']:
                json_content = json_content.replace(text, text.replace(".", ""))

        return json.loads(json_content)

    def _load_spec(self) -> dict[str, Any]:
        """
        Load OpenAPI specification from URL, file path or cache.

        Returns:
            Parsed OpenAPI specification as dictionary
        """
        # Try loading from URL first
        spec = self._get_spec_by_url()

        # Try loading from file path if URL failed
        if not spec:
            spec = self._get_spec_by_path()

        # Fall back to cache if both URL and path failed
        if not spec:
            spec = self._get_spec_from_cache()

        return spec

    def _get_spec_by_url(self) -> dict[str, Any] | None:
        """
        Try to load OpenAPI spec from URL.

        Returns:
            Parsed OpenAPI spec or None if failed
        """
        try:
            response = httpx.get(self.spec_path, timeout=5)
            response.raise_for_status()

            # Process and cache the spec
            spec = self._patch(response.json())
            with open(self.cache_spec_path, "w") as f:
                f.write(json.dumps(spec, indent=4, ensure_ascii=False))
            return spec

        except httpx.HTTPError:
            LOGGER.warning(f"OpenAPI spec not available by URL: {self.spec_path}")

            # Try to use local file as fallback
            file_path = (
                self.spec_path
                if Path(self.spec_path).is_file()
                else str(self.cache_spec_path)
            )

            if Path(file_path).is_file():
                LOGGER.warning(f"Trying to open OpenAPI spec from path: {file_path}")
                with open(file_path, "r") as f:
                    return self._patch(json.loads(f.read()))

            return None

    def _get_spec_from_cache(self) -> dict[str, Any]:
        """
        Load OpenAPI spec from cache.

        Returns:
            Parsed OpenAPI spec

        Raises:
            FileNotFoundError: If spec not found in cache
        """
        try:
            with open(self.cache_spec_path, "r") as f:
                spec = self._patch(json.loads(f.read()))
                self.spec_path = str(self.cache_spec_path)
                LOGGER.warning(f"OpenAPI spec loaded from cache: {self.spec_path}")
                return spec
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"OpenAPI spec not available from URL: {self.spec_path}, and not found in cache"
            ) from e

    def _get_spec_by_path(self) -> dict[str, Any] | None:
        """
        Try to load OpenAPI spec from file path.

        Returns:
            Parsed OpenAPI spec or None if file not found
        """
        try:
            with open(self.spec_path, "r") as f:
                return self._patch(json.loads(f.read()))
        except FileNotFoundError:
            LOGGER.warning(f"OpenAPI spec not found at local path: {self.spec_path}")
            return None

    def _extract_model_name(self, schema_ref: str | None) -> str | None:
        """
        Extract model name from schema reference.

        Args:
            schema_ref: Schema reference string

        Returns:
            Model name or None if no valid reference
        """
        if not schema_ref or "#/definitions/" not in schema_ref and "#/components/schemas/" not in schema_ref:
            return None

        # Use NamingUtils to ensure consistent class naming
        model_name = NamingUtils.to_class_name(schema_ref.split("/")[-1])
        return model_name

    def _get_request_body(self, request_body: dict[str, Any] | list[dict[str, Any]]) -> str | None:
        """
        Extract request body model from OpenAPI spec.

        Args:
            request_body: Request body specification

        Returns:
            Model name or None if no request body
        """
        # Handle Swagger 2.0 format (list of parameters)
        if isinstance(request_body, list):
            for parameter in request_body:
                if parameter.get("in") == ParamType.BODY:
                    schema_ref = parameter.get("schema", {}).get("$ref")
                    if schema_ref:
                        model_name = self._extract_model_name(schema_ref)
                        if model_name:
                            self.request_models.add(model_name)
                            return model_name
        # Handle OpenAPI 3.0 format
        else:
            for content_type in request_body.get("content", {}).keys():
                schema_ref = (
                    request_body.get("content", {})
                    .get(content_type, {})
                    .get("schema", {})
                    .get("$ref")
                )
                if schema_ref:
                    model_name = self._extract_model_name(schema_ref)
                    if model_name:
                        self.request_models.add(model_name)
                        return model_name

        return None

    def _get_response_body(self, response_body: dict[str, Any]) -> dict[str, str]:
        """
        Extract response models from OpenAPI spec.

        Args:
            response_body: Response specification

        Returns:
            Dictionary mapping status codes to model names
        """
        responses: dict[str, str] = {}

        if not response_body:
            return responses

        # Handle OpenAPI 3.0 format
        if self.openapi_version.startswith("3."):
            for status_code, response_spec in response_body.items():
                for content_type in response_spec.get("content", {}).keys():
                    schema_ref = (
                        response_spec
                        .get("content", {})
                        .get(content_type, {})
                        .get("schema", {})
                        .get("$ref")
                    )

                    model_name = self._extract_model_name(schema_ref)
                    if model_name:
                        responses[status_code] = model_name
                        self.response_models.add(model_name)

        # Handle Swagger 2.0 format
        elif self.openapi_version.startswith("2."):
            for status_code, response in response_body.items():
                schema_ref = response.get("schema", {}).get("$ref") or response.get("schema", {}).get("result")

                model_name = self._extract_model_name(schema_ref)
                if model_name:
                    responses[status_code] = model_name
                    self.response_models.add(model_name)

        return responses

    def _get_parameter_type(self, parameter: dict[str, Any]) -> str:
        """
        Get parameter type from OpenAPI spec.

        Args:
            parameter: Parameter specification

        Returns:
            Python type for the parameter
        """
        schema = parameter.get("schema", {})
        param_type = schema.get("type")

        if not param_type:
            # Handle $ref in schema
            ref = schema.get("$ref")
            if ref:
                return self._extract_model_name(ref)

            # Handle arrays
            items = schema.get("items", {})
            if items:
                item_type = items.get("type")
                if item_type:
                    return f"list[{TYPE_MAP.get(item_type, 'Any')}]"
                ref = items.get("$ref")
                if ref:
                    model_name = self._extract_model_name(ref)
                    return f"list[{model_name}]"

            return "Any"

        # Handle basic types
        if param_type in TYPE_MAP:
            return TYPE_MAP[param_type]

        # Handle arrays
        if param_type == "array":
            items = schema.get("items", {})
            item_type = items.get("type")
            if item_type:
                return f"list[{TYPE_MAP.get(item_type, 'Any')}]"
            ref = items.get("$ref")
            if ref:
                model_name = self._extract_model_name(ref)
                return f"list[{model_name}]"

        return "Any"

    def _process_parameter(self, parameter: dict[str, Any]) -> ParameterDict:
        """
        Process a parameter from OpenAPI spec.

        Args:
            parameter: Parameter specification

        Returns:
            Processed parameter dictionary
        """
        param_dict: ParameterDict = {
            "name": NamingUtils.to_param_name(parameter.get("name", "")),
            "type": self._get_parameter_type(parameter),
            "required": parameter.get("required", False),
        }

        # Add description if available
        if "description" in parameter:
            param_dict["description"] = parameter["description"]

        # Add default value if available
        if "default" in parameter.get("schema", {}):
            param_dict["default"] = parameter["schema"]["default"]

        return param_dict

    def _get_parameters(self, parameters: list[dict[str, Any]], param_type: ParamType) -> list[ParameterDict]:
        """
        Extract parameters of specified type from OpenAPI spec.

        Args:
            parameters: List of parameters
            param_type: Parameter type to extract

        Returns:
            List of processed parameters
        """
        return self._get_params_with_types(parameters, param_type)

    def _get_params_with_types(self, parameters: list[dict[str, Any]], param_type: ParamType) -> list[ParameterDict]:
        """
        Process parameters and extract type information.

        Args:
            parameters: List of parameters
            param_type: Parameter type to extract

        Returns:
            List of processed parameters with type information
        """
        if not parameters:
            return []

        params: list[ParameterDict] = []

        for parameter in parameters:
            # Skip parameters that don't match the requested type
            if parameter.get("in") != param_type:
                continue

            # Skip excluded parameters
            parameter_name = parameter.get("name")
            if parameter_name in self.EXCLUDED_PARAMS:
                continue

            # Process parameter
            param_dict = self._process_parameter(parameter)
            params.append(param_dict)

        return params

    def parse_openapi_spec(self) -> list[Handler]:
        """
        Parse OpenAPI specification and extract API endpoints.

        Returns:
            List of parsed handlers
        """
        # Extract metadata
        info = self.openapi_spec.get("info", {})
        self.version = info.get("version", "1.0.0")
        self.description = info.get("description", "")
        self.openapi_version = (
                self.openapi_spec.get("openapi", "") or
                self.openapi_spec.get("swagger", "")
        )

        # Warn about unsupported versions
        if self.openapi_version.startswith("2."):
            LOGGER.warning(
                "OpenAPI/Swagger version 2.0 is not fully supported. "
                "Consider converting to 3.0 with https://converter.swagger.io/ "
                "and set the local spec path in 'swagger' option in nuke.toml!"
            )

        # Process all paths and methods
        paths = self.openapi_spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                self._process_method(path, method, details)

        return self.handlers

    def _process_method(self, path: str, method: str, details: dict[str, Any]) -> None:
        """
        Process API method details and create handler.

        Args:
            path: API path
            method: HTTP method
            details: Method details
        """
        # Extract tags and add to all_tags
        tags = details.get("tags", [])
        self.all_tags.update(tags)

        # Extract basic metadata
        summary = details.get("summary", "")
        operation_id = details.get("operationId", "")
        parameters = details.get("parameters", [])

        # Process parameters by type
        query_parameters = self._get_parameters(parameters, ParamType.QUERY)
        path_parameters = self._get_parameters(parameters, ParamType.PATH)
        headers = self._get_parameters(parameters, ParamType.HEADER)

        # Process request body and responses
        request_body = self._get_request_body(
            details.get("requestBody", details.get("parameters", {}))
        )
        responses = self._get_response_body(details.get("responses", {}))

        # Create and store handler
        handler = Handler(
            path=self._normalize_swagger_path(path),
            method=method,
            tags=tags,
            summary=summary,
            operation_id=operation_id,
            query_parameters=query_parameters,
            headers=headers,
            path_parameters=path_parameters,
            request_body=request_body,
            responses=responses,
        )
        self.handlers.append(handler)

    def models_by_tag(self, tag: str) -> set[str]:
        """
        Get all models used by handlers with specified tag.

        Args:
            tag: API tag

        Returns:
            Set of model names
        """
        models = set()

        for handler in self.handlers:
            if tag not in handler.tags:
                continue

            # Extract models from path parameters
            if handler.path_parameters:
                for param in handler.path_parameters:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            # Extract models from query parameters
            if handler.query_parameters:
                for param in handler.query_parameters:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            # Extract models from headers
            if handler.headers:
                for param in handler.headers:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            # Add request body model
            if handler.request_body:
                models.add(handler.request_body)

            # Add response models
            if handler.responses:
                models.update(handler.responses.values())

        return models

    def handlers_by_tag(self, tag: str) -> list[Handler]:
        """Get handlers filtered by tag."""
        return [h for h in self.handlers if tag in h.tags]

    def handlers_by_method(self, method: str) -> list[Handler]:
        """Get handlers filtered by HTTP method."""
        return [h for h in self.handlers if h.method == method]

    def handler_by_path(self, path: str) -> list[Handler]:
        """Get handlers filtered by path."""
        return [h for h in self.handlers if h.path == path]

    @staticmethod
    def _normalize_swagger_path(path: str) -> str:
        """
        Normalize path parameters in swagger path.

        Args:
            path: Original path with parameters

        Returns:
            Normalized path with snake_case parameters
        """

        def replace_placeholder(match: re.Match) -> str:
            placeholder = match.group(0)[1:-1]
            return "{" + NamingUtils.to_param_name(placeholder) + "}" if placeholder else ""

        return re.sub(r"\{[^}]*\}", replace_placeholder, path)