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
from pydantic import BaseModel, Field, HttpUrl

from restcodegen.generator.log import LOGGER
from restcodegen.generator.naming import NamingUtils


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
    path_parameters: list[dict[str, Any]] | None = Field(
        None, description="Path parameters"
    )
    query_parameters: list[dict[str, Any]] | None = Field(
        None, description="Query parameters"
    )
    headers: list[dict[str, Any]] | None = Field(None, description="Header parameters")
    request_body: str | None = Field(None, description="Request body model name")
    content_type: str | None = Field(None, description="Request content type")
    form_data_parameters: list[dict[str, Any]] | None = Field(
        None, description="Form data parameters for multipart/form-data requests"
    )
    responses: dict[str, str] | None = Field(
        None, description="Response models by status code"
    )

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
        self.cache_spec_path = (
            self.cache_spec_dir / f"{NamingUtils.to_snake_case(self.service_name)}.json"
        )

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

    @staticmethod
    def _extract_model_name(schema_ref: str | None) -> str | None:
        """
        Extract model name from schema reference.

        Args:
            schema_ref: Schema reference string

        Returns:
            Model name or None if no valid reference
        """
        if (
            not schema_ref
            or "#/definitions/" not in schema_ref
            and "#/components/schemas/" not in schema_ref
        ):
            return None

        # Use NamingUtils to ensure consistent class naming
        model_name = NamingUtils.to_camel_case(schema_ref.split("/")[-1])
        return model_name

    def _get_request_body(
        self, request_body: dict[str, Any] | list[dict[str, Any]]
    ) -> tuple[str | None, str | None]:
        """
        Extract request body model from OpenAPI spec.

        Args:
            request_body: Request body specification

        Returns:
            Tuple of (model_name, content_type) or (None, None) if no request body
        """
        # Extract operation_id if present
        operation_id = ""
        if isinstance(request_body, dict) and "operation_id" in request_body:
            operation_id = request_body.pop("operation_id")

        # Handle Swagger 2.0 format (list of parameters)
        if isinstance(request_body, list):
            for parameter in request_body:
                if parameter.get("in") == ParamType.BODY:
                    schema_ref = parameter.get("schema", {}).get("$ref")
                    if schema_ref:
                        model_name = self._extract_model_name(schema_ref)
                        if model_name:
                            self.request_models.add(model_name)
                            return model_name, "application/json"

                    # Handle inline schema in Swagger 2.0
                    schema = parameter.get("schema", {})
                    if schema.get("type") == "object" and schema.get("properties"):
                        model_name = self._generate_inline_model_name(
                            operation_id, parameter.get("name", "")
                        )
                        self._create_inline_model(schema, model_name)
                        self.request_models.add(model_name)
                        return model_name, "application/json"
        # Handle OpenAPI 3.0 format
        else:
            for content_type in request_body.get("content", {}).keys():
                schema = (
                    request_body.get("content", {})
                    .get(content_type, {})
                    .get("schema", {})
                )

                # Проверяем наличие $ref
                schema_ref = schema.get("$ref")
                if schema_ref:
                    model_name = self._extract_model_name(schema_ref)
                    if model_name:
                        self.request_models.add(model_name)
                        return model_name, content_type

                # Обработка встроенных схем (inline schemas)
                if schema.get("type") == "object" and schema.get("properties"):
                    model_name = self._generate_inline_model_name(operation_id)
                    self._create_inline_model(schema, model_name)
                    self.request_models.add(model_name)
                    return model_name, content_type

        return None, None

    @staticmethod
    def _generate_inline_model_name(operation_id: str, param_name: str = "") -> str:
        if operation_id:
            return f"{NamingUtils.to_camel_case(operation_id)}Request"
        elif param_name:
            return f"{NamingUtils.to_camel_case(param_name)}Model"
        else:
            return "RequestBodyModel"

    def _create_inline_model(self, schema: dict[str, Any], model_name: str) -> None:
        if "components" not in self.openapi_spec:
            self.openapi_spec["components"] = {}

        if "schemas" not in self.openapi_spec["components"]:
            self.openapi_spec["components"]["schemas"] = {}

        self.openapi_spec["components"]["schemas"][model_name] = schema

        LOGGER.info(f"Created inline model: {model_name}")

    def _get_response_body(self, response_body: dict[str, Any]) -> dict[str, str]:
        responses: dict[str, str] = {}

        if not response_body:
            return responses

        operation_id = ""
        if "operation_id" in response_body:
            operation_id = response_body.pop("operation_id")

        # Handle OpenAPI 3.0 format
        if self.openapi_version.startswith("3."):
            for status_code, response_spec in response_body.items():
                for content_type in response_spec.get("content", {}).keys():
                    schema = (
                        response_spec.get("content", {})
                        .get(content_type, {})
                        .get("schema", {})
                    )

                    schema_ref = schema.get("$ref")
                    if schema_ref:
                        model_name = self._extract_model_name(schema_ref)
                        if model_name:
                            responses[status_code] = model_name
                            self.response_models.add(model_name)
                            continue

                    if schema.get("type") == "object" and schema.get("properties"):
                        model_name = self._generate_inline_response_model_name(
                            operation_id, status_code
                        )
                        self._create_inline_model(schema, model_name)
                        responses[status_code] = model_name
                        self.response_models.add(model_name)

        # Handle Swagger 2.0 format
        elif self.openapi_version.startswith("2."):
            for status_code, response in response_body.items():
                schema = response.get("schema", {})

                schema_ref = schema.get("$ref") or schema.get("result")
                if schema_ref:
                    model_name = self._extract_model_name(schema_ref)
                    if model_name:
                        responses[status_code] = model_name
                        self.response_models.add(model_name)
                        continue

                if schema.get("type") == "object" and schema.get("properties"):
                    model_name = self._generate_inline_response_model_name(
                        operation_id, status_code
                    )
                    self._create_inline_model(schema, model_name)
                    responses[status_code] = model_name
                    self.response_models.add(model_name)

        return responses

    @staticmethod
    def _generate_inline_response_model_name(
        operation_id: str, status_code: str
    ) -> str:
        status_name = {
            "200": "Success",
            "201": "Created",
            "202": "Accepted",
            "204": "NoContent",
            "400": "BadRequest",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "NotFound",
            "500": "ServerError",
        }.get(status_code, f"Status{status_code}")

        if operation_id:
            return f"{NamingUtils.to_camel_case(operation_id)}{status_name}Response"
        else:
            return f"{status_name}Response"

    def _get_parameter_type(self, parameter: dict[str, Any]) -> str:
        schema = parameter.get("schema", {})
        param_type = schema.get("type")

        if not param_type:
            # Handle $ref in schema
            ref = schema.get("$ref")
            if ref:
                return self._extract_model_name(ref)

            # Handle allOf with $ref in schema
            all_of = schema.get("allOf")
            if all_of and isinstance(all_of, list):
                for item in all_of:
                    ref = item.get("$ref")
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

        if param_type in TYPE_MAP:
            return TYPE_MAP[param_type]

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
        param_dict: ParameterDict = {
            "name": parameter.get("name", ""),
            "type": self._get_parameter_type(parameter),
            "required": parameter.get("required", False),
        }

        if "description" in parameter:
            param_dict["description"] = parameter["description"]

        if "default" in parameter.get("schema", {}):
            param_dict["default"] = parameter["schema"]["default"]

        return param_dict

    def _get_parameters(
        self, parameters: list[dict[str, Any]], param_type: ParamType
    ) -> list[ParameterDict]:
        """
        Extract parameters of specified type from OpenAPI spec.

        Args:
            parameters: List of parameters
            param_type: Parameter type to extract

        Returns:
            List of processed parameters
        """
        return self._get_params_with_types(parameters, param_type)

    def _get_params_with_types(
        self, parameters: list[dict[str, Any]], param_type: ParamType
    ) -> list[ParameterDict]:
        if not parameters:
            return []

        params: list[ParameterDict] = []

        for parameter in parameters:
            if parameter.get("in") != param_type:
                continue

            parameter_name = parameter.get("name")
            if parameter_name in self.EXCLUDED_PARAMS:
                continue

            param_dict = self._process_parameter(parameter)
            params.append(param_dict)

        return params

    @staticmethod
    def _extract_form_data_parameters(schema: dict[str, Any]) -> list[dict[str, Any]]:
        form_params = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for name, prop in properties.items():
            param_type = prop.get("type", "string")
            description = prop.get("description", "")
            format_type = prop.get("format", "")

            # Определяем тип параметра на основе type и format
            if param_type == "string" and format_type == "binary":
                python_type = "bytes"
            elif param_type == "integer":
                python_type = "int"
            elif param_type == "number":
                python_type = "float"
            elif param_type == "boolean":
                python_type = "bool"
            elif param_type == "array":
                items_type = prop.get("items", {}).get("type", "string")
                if items_type == "string":
                    python_type = "list[str]"
                elif items_type == "integer":
                    python_type = "list[int]"
                elif items_type == "number":
                    python_type = "list[float]"
                else:
                    python_type = "list"
            else:
                python_type = "str"

            form_params.append(
                {
                    "name": name,
                    "type": python_type,
                    "description": description,
                    "required": name in required,
                    "format": format_type,
                }
            )

        return form_params

    def parse_openapi_spec(self) -> list[Handler]:
        info = self.openapi_spec.get("info", {})
        self.version = info.get("version", "1.0.0")
        self.description = info.get("description", "")
        self.openapi_version = self.openapi_spec.get(
            "openapi", ""
        ) or self.openapi_spec.get("swagger", "")

        if self.openapi_version.startswith("2."):
            LOGGER.warning(
                "OpenAPI/Swagger version 2.0 is not fully supported. "
                "Consider converting to 3.0 with https://converter.swagger.io/ "
                "and set the local spec path in 'swagger' option in nuke.toml!"
            )

        paths = self.openapi_spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                self._process_method(path, method, details)

        return self.handlers

    def _process_method(self, path: str, method: str, details: dict[str, Any]) -> None:
        tags = [
            NamingUtils.to_camel_case(NamingUtils.to_snake_case(tag))
            for tag in details.get("tags", [])
        ]
        self.all_tags.update(tags)

        summary = details.get("summary", "")
        operation_id = details.get("operationId", "")
        parameters = details.get("parameters", [])

        query_parameters = self._get_parameters(parameters, ParamType.QUERY)
        path_parameters = self._get_parameters(parameters, ParamType.PATH)
        headers = self._get_parameters(parameters, ParamType.HEADER)

        if not path_parameters:
            path_parameters = self._extract_path_params_from_url(path)

        request_body_data = details.get("requestBody", details.get("parameters", {}))

        # Добавляем operation_id в request_body_data для использования в _get_request_body
        if isinstance(request_body_data, dict) and operation_id:
            request_body_data["operation_id"] = operation_id

        request_body, content_type = self._get_request_body(request_body_data)

        # Add operation_id to responses for inline model generation
        responses_data = details.get("responses", {})
        if operation_id:
            responses_data["operation_id"] = operation_id

        responses = self._get_response_body(responses_data)

        form_data_parameters = None
        if content_type == "multipart/form-data" and isinstance(
            request_body_data, dict
        ):
            schema = (
                request_body_data.get("content", {})
                .get("multipart/form-data", {})
                .get("schema", {})
            )
            form_data_parameters = self._extract_form_data_parameters(schema)

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
            content_type=content_type,
            form_data_parameters=form_data_parameters,
            responses=responses,
        )
        self.handlers.append(handler)

    @staticmethod
    def _extract_path_params_from_url(path: str) -> list:
        params = []
        path_params = re.findall(r"\{([^}]+)\}", path)

        for param in path_params:
            param_name = NamingUtils.to_snake_case(param)
            params.append(
                {
                    "name": param_name,
                    "type": "str",
                    "description": f"Path parameter: {param_name}",
                    "required": True,
                }
            )

        return params

    def models_by_tag(self, tag: str) -> set[str]:
        models = set()

        for handler in self.handlers:
            if tag not in handler.tags:
                continue

            if handler.path_parameters:
                for param in handler.path_parameters:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            if handler.query_parameters:
                for param in handler.query_parameters:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            if handler.headers:
                for param in handler.headers:
                    param_type = param["type"]
                    if param_type not in TYPE_MAP.values():
                        models.add(param_type)

            if handler.request_body:
                models.add(handler.request_body)

            if handler.responses:
                models.update(handler.responses.values())

        return models

    def handlers_by_tag(self, tag: str) -> list[Handler]:
        return [h for h in self.handlers if tag in h.tags]

    def handlers_by_method(self, method: str) -> list[Handler]:
        return [h for h in self.handlers if h.method == method]

    def handler_by_path(self, path: str) -> list[Handler]:
        return [h for h in self.handlers if h.path == path]

    @staticmethod
    def _normalize_swagger_path(path: str) -> str:
        def replace_placeholder(match: re.Match) -> str:
            placeholder = match.group(0)[1:-1]
            return (
                f"{{{NamingUtils.to_param_name(placeholder)}}}" if placeholder else ""
            )

        return re.sub(r"\{[^}]*\}", replace_placeholder, path)
