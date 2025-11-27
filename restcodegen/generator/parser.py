from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, Dict

from datamodel_code_generator import OpenAPIScope, PythonVersion
from datamodel_code_generator.parser.openapi import (
    OpenAPIParser,
    Operation,
    ParameterObject,
    ReferenceObject,
    RequestBodyObject,
    ResponseObject,
)

from restcodegen.generator.log import LOGGER
from restcodegen.generator.utils import name_to_snake, rename_python_builtins, snake_to_camel
from pydantic import BaseModel, ConfigDict
from restcodegen.generator.spec.loader import SpecLoader


OPERATION_NAMES: set[str] = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

TYPE_MAP = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "boolean": "bool",
    "array": "list",
    "object": "Any",
}


@dataclass(slots=True)
class ParsedOperation:
    path: str
    method: str
    operation: Operation
    parameters: list[ParameterObject]
    request_body: RequestBodyObject | None
    responses: dict[str, ResponseObject]
    raw_operation: dict[str, Any]


class OperationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    operation: Operation
    method: str
    path: str
    raw_path: str
    tags: list[str]
    summary: str | None
    operation_id: str
    parameters: dict[str, list[dict[str, Any]]]
    request_body_model: str | None
    responses: dict[str, str]
    success_response: str | None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class Parser:
    BASE_PATH = Path.cwd() / "clients" / "http"

    def __init__(
        self,
        openapi_spec: dict[str, Any],
        service_name: str,
        selected_tags: list[str] | None = None,
    ) -> None:
        self.openapi_spec = openapi_spec
        self._raw_spec = openapi_spec
        self._service_name = service_name
        self.version: str = ""
        self.description: str = ""
        self.openapi_version: str = ""
        self._selected_tags: set[str] = set(selected_tags) if selected_tags else set()
        self.all_tags: set[str] = set()
        self.request_model_names: set[str] = set()
        self.response_model_names: set[str] = set()
        self._operations: list[ParsedOperation] | None = None
        self.parse()

    @classmethod
    def from_source(
        cls,
        openapi_spec: str,
        package_name: str,
        *,
        selected_tags: list[str] | None = None,
        loader: SpecLoader | None = None,
    ) -> "Parser":
        spec_loader = loader or SpecLoader(openapi_spec, package_name)
        spec = spec_loader.open()
        return cls(spec, package_name, selected_tags=selected_tags)

    @property
    def apis(self) -> set[str]:
        if not self._selected_tags:
            return self.all_tags

        result_tags = {tag for tag in self._selected_tags if tag in self.all_tags}
        if not result_tags:
            LOGGER.warning(
                "Ни один из выбранных тегов не найден в спецификации. Будут использованы все доступные теги."
            )
            return self.all_tags

        return result_tags

    @property
    def service_name(self) -> str:
        return self._service_name

    def parse(self) -> list[ParsedOperation]:
        info = self.openapi_spec.get("info", {})
        self.version = info.get("version", "1.0.0")
        self.description = info.get("description", "")
        self.openapi_version = self.openapi_spec.get("openapi", "") or self.openapi_spec.get("swagger", "")

        if self.openapi_version.startswith("2."):
            LOGGER.warning(
                "OpenAPI/Swagger version 2.0 требует конвертации в 3.x. "
                "Пожалуйста, обновите спецификацию перед генерацией."
            )

        parser = self._init_openapi_parser()
        operations = self._collect_operations(parser)
        tags, request_models, response_models = self._collect_metadata(operations)

        self._operations = operations
        self.all_tags = tags
        self.request_model_names = request_models
        self.response_model_names = response_models
        return operations

    @property
    def operations(self) -> list[ParsedOperation]:
        return list(self._operations or [])

    def get_operation_context(self, operation: ParsedOperation) -> OperationContext:
        parameters = self._build_parameters(operation)
        if not parameters["path"]:
            parameters["path"] = self._fallback_path_parameters(operation.path)

        responses = self._extract_response_models(operation.responses)
        request_body_model = self._extract_request_body_model(operation)
        success_response = self._get_success_response(responses)

        operation_id = operation.operation.operationId or self._generate_operation_id(operation)

        return OperationContext(
            operation=operation.operation,
            method=operation.method,
            path=self._normalize_path(operation.path),
            raw_path=operation.path,
            tags=operation.operation.tags or [],
            summary=operation.operation.summary,
            operation_id=operation_id,
            parameters=parameters,
            request_body_model=request_body_model,
            responses=responses,
            success_response=success_response,
        )

    def handlers_by_tag(self, tag: str) -> list[ParsedOperation]:
        return [operation for operation in self.operations if tag in (operation.operation.tags or [])]

    def handlers_by_method(self, method: str) -> list[ParsedOperation]:
        return [operation for operation in self.operations if operation.method.lower() == method.lower()]

    def handler_by_path(self, path: str) -> list[ParsedOperation]:
        normalized = self._normalize_path(path)
        return [operation for operation in self.operations if self._normalize_path(operation.path) == normalized]

    def request_models(self) -> set[str]:
        return set(self.request_model_names)

    def response_models(self) -> set[str]:
        return set(self.response_model_names)

    def models_by_tag(self, tag: str) -> set[str]:
        models: set[str] = set()
        for operation in self.operations:
            if tag in (operation.operation.tags or []):
                request_model = self._extract_request_body_model(operation)
                if request_model:
                    models.add(request_model)
                responses = self._extract_response_models(operation.responses)
                models.update(responses.values())
                for parameter in operation.parameters:
                    param_type = self._extract_parameter_type(parameter)
                    if self._is_complex_type(param_type):
                        models.add(param_type)
        return models

    def _init_openapi_parser(self) -> OpenAPIParser:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp_file:
            json.dump(self._raw_spec, tmp_file)
            tmp_path = Path(tmp_file.name)

        try:
            parser = OpenAPIParser(
                tmp_path,
                target_python_version=PythonVersion.PY_310,
                openapi_scopes=[OpenAPIScope.Schemas, OpenAPIScope.Paths],
                include_path_parameters=True,
            )
            parser.parse()
        finally:
            tmp_path.unlink(missing_ok=True)

        return parser

    @staticmethod
    def _collect_operations(parser: OpenAPIParser) -> list[ParsedOperation]:
        operations: list[ParsedOperation] = []
        raw_paths: Dict[str, Dict[str, Any]] = parser.raw_obj.get("paths", {})  # type: ignore[assignment]
        for path, methods in raw_paths.items():
            if not isinstance(methods, dict):
                continue

            for method, raw_operation in methods.items():
                if method not in OPERATION_NAMES:
                    continue

                operation = Operation.model_validate(raw_operation)
                resolved_parameters: list[ParameterObject] = []
                for parameter in operation.parameters:
                    if isinstance(parameter, ReferenceObject):
                        resolved_param = parser.get_ref_model(parameter.ref)
                        resolved_parameters.append(ParameterObject.model_validate(resolved_param))
                    else:
                        resolved_parameters.append(parameter)

                request_body: RequestBodyObject | None = None
                if operation.requestBody is not None:
                    if isinstance(operation.requestBody, ReferenceObject):
                        ref_body = parser.get_ref_model(operation.requestBody.ref)
                        request_body = RequestBodyObject.model_validate(ref_body)
                    else:
                        request_body = operation.requestBody

                resolved_responses: dict[str, ResponseObject] = {}
                for status_code, response in operation.responses.items():
                    if isinstance(response, ReferenceObject):
                        ref_response = parser.get_ref_model(response.ref)
                        resolved_responses[str(status_code)] = ResponseObject.model_validate(ref_response)
                    else:
                        resolved_responses[str(status_code)] = response

                operations.append(
                    ParsedOperation(
                        path=path,
                        method=method,
                        operation=operation,
                        parameters=resolved_parameters,
                        request_body=request_body,
                        responses=resolved_responses,
                        raw_operation=raw_operation,
                    )
                )

        return operations

    def _collect_metadata(self, operations: list[ParsedOperation]) -> tuple[set[str], set[str], set[str]]:
        tags: set[str] = set()
        request_models: set[str] = set()
        response_models: set[str] = set()

        for operation in operations:
            tags.update(operation.operation.tags or [])
            request_body_model = self._extract_request_body_model(operation)
            if request_body_model:
                request_models.add(request_body_model)

            responses = self._extract_response_models(operation.responses)
            response_models.update(responses.values())

        return tags, request_models, response_models

    @staticmethod
    def _normalize_path(path: str) -> str:
        def replace_placeholder(match: re.Match[str]) -> str:
            placeholder = match.group(0)[1:-1]
            if not placeholder:
                return ""
            return "{" + rename_python_builtins(name_to_snake(placeholder)) + "}"

        return re.sub(r"\{[^}]*\}", replace_placeholder, path)

    @staticmethod
    def _extract_parameter_type(parameter: ParameterObject) -> str:
        schema = parameter.schema_
        if schema and schema.ref:
            return Parser._ref_to_model_name(schema.ref)
        if schema and schema.type:
            schema_type = schema.type.value if hasattr(schema.type, "value") else schema.type
            if isinstance(schema_type, list):
                schema_type = schema_type[0]
            mapped = TYPE_MAP.get(str(schema_type).lower())
            if mapped:
                return mapped
            return str(schema_type)
        return "Any"

    def _extract_request_body_model(self, operation: ParsedOperation) -> str | None:
        if not operation.request_body:
            return None
        for media in operation.request_body.content.values():
            schema = media.schema_
            if isinstance(schema, ReferenceObject):
                return self._ref_to_model_name(schema.ref)
            if schema and schema.ref:
                return self._ref_to_model_name(schema.ref)
        return None

    @staticmethod
    def _ref_to_model_name(ref: str) -> str:
        name = ref.split("/")[-1]
        return snake_to_camel(name)

    @staticmethod
    def _extract_response_models(responses: dict[str, ResponseObject]) -> dict[str, str]:
        result: dict[str, str] = {}
        for status_code, response in responses.items():
            status_str = str(status_code)
            if not Parser._is_success_status(status_str):
                continue
            for media in response.content.values():
                schema = media.schema_
                if isinstance(schema, ReferenceObject):
                    result[status_str] = Parser._ref_to_model_name(schema.ref)
                    break
                if schema and schema.ref:
                    result[status_str] = Parser._ref_to_model_name(schema.ref)
                    break
        return result

    @staticmethod
    def _extract_parameter_location(parameter: ParameterObject) -> str:
        if parameter.in_:
            return parameter.in_.value
        return "query"

    def _build_parameters(self, operation: ParsedOperation) -> dict[str, list[dict[str, Any]]]:
        path_params: list[dict[str, Any]] = []
        query_params: list[dict[str, Any]] = []
        header_params: list[dict[str, Any]] = []

        for parameter in operation.parameters:
            context = self._build_parameter_context(parameter)
            location = context["location"]
            if location == "path":
                path_params.append(context)
            elif location == "header":
                header_params.append(context)
            else:
                query_params.append(context)

        return {
            "path": self._sort_parameters(path_params),
            "query": self._sort_parameters(query_params),
            "header": self._sort_parameters(header_params),
        }

    def _build_parameter_context(self, parameter: ParameterObject) -> dict[str, Any]:
        name = parameter.name or "param"
        python_name = rename_python_builtins(name_to_snake(name))
        type_str = self._extract_parameter_type(parameter)
        description = parameter.description or ""
        default: Any | None = None
        if parameter.schema_ and parameter.schema_.default is not None:
            default = parameter.schema_.default
        location = self._extract_parameter_location(parameter)

        if not python_name:
            fallback_source = f"{location}_{name}" if name else f"{location}_param"
            python_name = rename_python_builtins(name_to_snake(fallback_source)) or f"{location}_param"

        return {
            "name": name,
            "python_name": python_name,
            "type": type_str,
            "required": bool(parameter.required),
            "description": description,
            "default": default,
            "location": location,
        }

    @staticmethod
    def _sort_parameters(parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(parameters, key=lambda item: not item["required"])

    @staticmethod
    def _fallback_path_parameters(path: str) -> list[dict[str, Any]]:
        params: list[dict[str, Any]] = []
        for index, match in enumerate(re.findall(r"\{([^}]+)\}", path), start=1):
            python_name = rename_python_builtins(name_to_snake(match))
            if not python_name:
                python_name = f"path_param_{index}"
            params.append(
                {
                    "name": match,
                    "python_name": python_name,
                    "type": "str",
                    "required": True,
                    "description": f"Path parameter: {match}",
                    "default": None,
                    "location": "path",
                }
            )
        return params

    @staticmethod
    def _get_success_response(responses: dict[str, str]) -> str | None:
        for status in ("200", "201", "202"):
            if status in responses:
                return responses[status]
        return None

    @staticmethod
    def _is_success_status(status_code: str) -> bool:
        if status_code.lower() == "default":
            return False
        normalized = status_code.upper()
        if normalized.endswith("XX") and len(normalized) == 3 and normalized[0].isdigit():
            normalized = normalized[0] + "00"
        if not normalized.isdigit():
            return False
        return 200 <= int(normalized) < 300

    @staticmethod
    def _generate_operation_id(operation: ParsedOperation) -> str:
        normalized_path = Parser._normalize_path(operation.path).strip("/")
        if normalized_path:
            segments = [segment.replace("_", "__") for segment in normalized_path.split("/") if segment]
            escaped_path = "_".join(segments) or "root"
        else:
            escaped_path = "root"

        candidate = f"{operation.method}_{escaped_path}"
        return rename_python_builtins(name_to_snake(candidate))

    @staticmethod
    def _is_complex_type(type_name: str) -> bool:
        builtin_types = {"int", "float", "str", "bool", "list", "dict", "Any"}
        return type_name not in builtin_types
