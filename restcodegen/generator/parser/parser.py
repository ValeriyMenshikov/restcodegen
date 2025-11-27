from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

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
from restcodegen.generator.parser.types import BaseParameter, Handler, ParameterType
from restcodegen.generator.utils import name_to_snake, rename_python_builtins, snake_to_camel

if TYPE_CHECKING:
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

DEFAULT_HEADER_VALUE_MAP = {"int": 0, "float": 0.0, "str": "", "bool": True}


@dataclass(slots=True)
class ParsedOperation:
    path: str
    method: str
    operation: Operation
    parameters: list[ParameterObject]
    request_body: RequestBodyObject | None
    responses: dict[str, ResponseObject]
    raw_operation: dict[str, Any]


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
        self.handlers: list[Handler] = []
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
        from restcodegen.generator.spec.loader import SpecLoader

        spec_loader = loader or SpecLoader(openapi_spec, package_name)
        spec = spec_loader.open()
        return cls(spec, package_name, selected_tags=selected_tags)

    @property
    def apis(self) -> set[str]:
        if not self._selected_tags:
            return self.all_tags

        result_tags = {tag for tag in self._selected_tags if tag in self.all_tags}
        if not result_tags:
            LOGGER.warning("Ни один из выбранных тегов не найден в спецификации. Будут использованы все доступные теги.")
            return self.all_tags

        return result_tags

    @property
    def service_name(self) -> str:
        return self._service_name

    def parse(self) -> list[Handler]:
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
        handlers, tags, request_models, response_models = self._build_handlers(operations)

        self._operations = operations
        self.handlers = handlers
        self.all_tags = tags
        self.request_model_names = request_models
        self.response_model_names = response_models
        return self.handlers

    @property
    def operations(self) -> list[ParsedOperation]:
        return list(self._operations or [])

    def handlers_by_tag(self, tag: str) -> list[Handler]:
        return [h for h in self.handlers if tag in h.tags]

    def handlers_by_method(self, method: str) -> list[Handler]:
        return [h for h in self.handlers if h.method == method]

    def handler_by_path(self, path: str) -> list[Handler]:
        return [h for h in self.handlers if h.path == path]

    def request_models(self) -> set[str]:
        return set(self.request_model_names)

    def response_models(self) -> set[str]:
        return set(self.response_model_names)

    def models_by_tag(self, tag: str) -> set[str]:
        models: set[str] = set()
        for handler in self.handlers:
            if tag in handler.tags:
                if handler.request_body:
                    models.add(handler.request_body)
                if handler.responses:
                    models.update(handler.responses.values())
                for param_group in (handler.path_parameters, handler.query_parameters, handler.headers):
                    if not param_group:
                        continue
                    for param in param_group:
                        models.add(param.type)
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

    def _collect_operations(self, parser: OpenAPIParser) -> list[ParsedOperation]:
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

    def _build_handlers(self, operations: list[ParsedOperation]) -> tuple[list[Handler], set[str], set[str], set[str]]:
        handlers: list[Handler] = []
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

            path_params, query_params, header_params = self._split_parameters(operation.parameters)
            if not path_params:
                path_params = self._extract_path_params_from_path(operation.path)

            handler = Handler(
                path=self._normalize_path(operation.path),
                method=operation.method,
                tags=operation.operation.tags or [],
                summary=operation.operation.summary,
                operation_id=operation.operation.operationId,
                path_parameters=path_params,
                query_parameters=query_params,
                headers=header_params,
                request_body=request_body_model,
                responses=responses,
            )
            handlers.append(handler)

        return handlers, tags, request_models, response_models

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
        if schema and schema.type:
            schema_type = schema.type.value if hasattr(schema.type, "value") else schema.type
            if isinstance(schema_type, list):
                schema_type = schema_type[0]
            mapped = TYPE_MAP.get(str(schema_type).lower())
            if mapped:
                return mapped
            return str(schema_type)
        return "str"

    @classmethod
    def _build_parameter(cls, parameter: ParameterObject) -> BaseParameter:
        in_location = ParameterType(parameter.in_.value if parameter.in_ else ParameterType.QUERY.value)
        type_str = cls._extract_parameter_type(parameter)
        default = DEFAULT_HEADER_VALUE_MAP.get(type_str)
        if parameter.schema_ and parameter.schema_.default is not None:
            default = parameter.schema_.default
        return BaseParameter(
            name=parameter.name or "param",
            type_=type_str,
            description=parameter.description or "",
            required=parameter.required,
            default=default if in_location == ParameterType.HEADER else None,
        )

    @staticmethod
    def _extract_request_body_model(operation: ParsedOperation) -> str | None:
        if not operation.request_body:
            return None
        for media in operation.request_body.content.values():
            schema = media.schema_
            if isinstance(schema, ReferenceObject):
                return Parser._ref_to_model_name(schema.ref)
            if schema and schema.ref:
                return Parser._ref_to_model_name(schema.ref)
        return None

    @staticmethod
    def _ref_to_model_name(ref: str) -> str:
        name = ref.split("/")[-1]
        return snake_to_camel(name)

    @staticmethod
    def _extract_response_models(responses: dict[str, ResponseObject]) -> dict[str, str]:
        result: dict[str, str] = {}
        for status_code, response in responses.items():
            for media in response.content.values():
                schema = media.schema_
                if isinstance(schema, ReferenceObject):
                    result[status_code] = Parser._ref_to_model_name(schema.ref)
                elif schema and schema.ref:
                    result[status_code] = Parser._ref_to_model_name(schema.ref)
        return result

    @staticmethod
    def _extract_path_params_from_path(path: str) -> list[BaseParameter]:
        params: list[BaseParameter] = []
        for match in re.findall(r"\{([^}]+)\}", path):
            normalized_name = rename_python_builtins(name_to_snake(match))
            params.append(
                BaseParameter(
                    name=normalized_name,
                    type_="str",
                    description=f"Path parameter: {normalized_name}",
                    required=True,
                )
            )
        return params

    @classmethod
    def _split_parameters(cls, parameters: list[ParameterObject]) -> Tuple[list[BaseParameter], list[BaseParameter], list[BaseParameter]]:
        path_params: list[BaseParameter] = []
        query_params: list[BaseParameter] = []
        header_params: list[BaseParameter] = []

        for parameter in parameters:
            built = cls._build_parameter(parameter)
            location = parameter.in_.value if parameter.in_ else "query"
            if location == ParameterType.PATH.value:
                path_params.append(built)
            elif location == ParameterType.HEADER.value:
                header_params.append(built)
            else:
                query_params.append(built)

        def sort_params(items: list[BaseParameter]) -> list[BaseParameter]:
            return sorted(items, key=lambda param: not param.required)

        return sort_params(path_params), sort_params(query_params), sort_params(header_params)
