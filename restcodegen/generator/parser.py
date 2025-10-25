import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from restcodegen.generator.log import LOGGER
from restcodegen.generator.parameters import (
    BaseParameter,
    ParameterType,
)
from restcodegen.generator.spec_loader import SpecLoader
from restcodegen.generator.utils import (
    name_to_snake,
    rename_python_builtins,
    snake_to_camel,
)

TYPE_MAP = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "boolean": "bool",
    "array": "list",
    "anyof": "str",
    "none": "Any",
}

DEFAULT_HEADER_VALUE_MAP = {"int": 0, "float": 0.0, "str": "", "bool": True}


class Handler(BaseModel):
    path: str = Field(...)
    method: str = Field(...)
    tags: list = Field(...)
    summary: str | None = Field(None)
    operation_id: str | None = Field(None)
    path_parameters: list[BaseParameter] | None = Field(None)
    query_parameters: list[BaseParameter] | None = Field(None)
    headers: list[BaseParameter] | None = Field(None)
    request_body: str | None = Field(None)
    responses: dict | None = Field(None)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class OpenApiSpec(BaseModel):
    service_name: str = Field(...)
    version: str = Field(...)
    title: str = Field(...)
    description: str = Field(...)
    openapi_version: str = Field(...)
    handlers: list[Handler]
    request_models: set[str] = set()
    response_models: set[str] = set()
    api_tags: set[str] = set()
    all_tags: set[str] = set()


class Parser:
    BASE_PATH = Path.cwd() / "clients" / "http"

    def __init__(
        self,
        openapi_spec: str | HttpUrl,
        service_name: str,
        selected_tags: list[str] | None = None,
    ) -> None:
        self._spec_path = str(openapi_spec)

        self._service_name = service_name
        self.openapi_spec: dict = SpecLoader(self._spec_path, self._service_name).open()
        self.version: str = ""
        self.description: str = ""
        self.openapi_version: str = ""
        self.handlers: list[Handler] = []
        self._selected_tags: set[str] = set(selected_tags) if selected_tags else set()
        self.all_tags: set[str] = set()
        self.parse()

    @property
    def apis(self) -> set[str]:
        result_tags = set()
        for tag in self._selected_tags:
            if tag not in self.all_tags:
                LOGGER.warning(f"Tag {tag} not found in openapi spec")
            else:
                result_tags.add(tag)

        if not result_tags and self._selected_tags:
            LOGGER.warning("Tags not found in openapi spec, used default tags")
            return self.all_tags
        elif not result_tags and not self._selected_tags:
            return self.all_tags

        return result_tags

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def client_type(self) -> str:
        return "http"

    def _get_request_body(self, request_body: dict | list) -> str | None:
        if isinstance(request_body, list):
            for parameter in request_body:
                if parameter.get("in") == "body":
                    schema = parameter.get("schema", {}).get("$ref", None)
                    if schema:
                        model_path = snake_to_camel(schema.split("/")[-1])
                        model_name = model_path[0].upper() + model_path[1:]
                        return model_name
        else:
            for content_type in request_body.get("content", {}).keys():
                schema = request_body.get("content", {}).get(content_type, {}).get("schema", {}).get("$ref", None)
                if schema:
                    model_name = snake_to_camel(schema.split("/")[-1])
                    return model_name
        return None

    def _get_response_body(self, response_body: dict) -> dict:
        responses: dict = {}
        if response_body:
            if self.openapi_version.startswith("3."):
                for status_code in response_body:
                    for content_type in response_body.get(status_code, {}).get("content", {}).keys():
                        schema = (
                            response_body.get(status_code, {})
                            .get("content", {})
                            .get(content_type, {})
                            .get("schema", {})
                            .get("$ref", None)
                        )
                        model_name = schema.split("/")[-1] if schema else None
                        if model_name:
                            model_name = snake_to_camel(model_name)
                            responses[status_code] = model_name
            elif self.openapi_version.startswith("2."):
                for status_code, response in response_body.items():
                    ref_schema = response.get("schema", {}).get("$ref")
                    result_schema = response.get("schema", {}).get("result")
                    schema = ref_schema or result_schema
                    if schema:
                        model = snake_to_camel(schema.split("/")[-1])
                        responses[status_code] = model
                        model_name = model[0].upper() + model[1:]
                        responses[status_code] = model_name
        return responses

    def _get_headers(self, parameters: list[dict]) -> list[BaseParameter]:
        params = self._get_params_with_types(parameters, param_type=ParameterType.HEADER)
        return params

    def _get_path_parameters(self, parameters: list[dict]) -> list[BaseParameter]:
        params = self._get_params_with_types(parameters, param_type=ParameterType.PATH)
        return params

    def _get_query_parameters(self, parameters: list[dict]) -> list[BaseParameter]:
        params = self._get_params_with_types(parameters, param_type=ParameterType.QUERY)
        return params

    @staticmethod
    def _get_params_with_types(parameters: list[dict], param_type: ParameterType) -> list[BaseParameter]:
        params: list[BaseParameter] = []
        if not parameters:
            return params
        for parameter in parameters:
            if parameter.get("in") == param_type:
                parameter_type = parameter.get("schema", {})
                any_of = parameter_type.get("anyOf")
                enum = parameter_type.get("$ref")

                parameter_type = parameter_type.get("type")
                parameter_name = parameter.get("name")
                parameter_description = parameter.get("description", "")
                parameter_is_required = parameter.get("required", False)

                if any_of:
                    parameter_type = "anyof"
                if enum:
                    parameter_type = enum.split("/")[-1]

                # Пропускаем параметр, если имя не определено
                if parameter_name is None:
                    continue

                parameter_with_desc = BaseParameter(
                    name=parameter_name,
                    type_=parameter_type if enum else TYPE_MAP[str(parameter_type).lower()],
                    description=parameter_description,
                    required=parameter_is_required,
                    default=DEFAULT_HEADER_VALUE_MAP.get(TYPE_MAP.get(parameter_type, "")),
                )

                params.append(parameter_with_desc)

        return params

    @staticmethod
    def _normalize_swagger_path(path: str, fix_builtins: bool = True) -> str:
        def replace_placeholder(match: re.Match) -> str:
            placeholder = match.group(0)[1:-1]
            if not placeholder:
                return ""

            return (
                f"{{{rename_python_builtins(name_to_snake(placeholder))}}}"
                if fix_builtins
                else f"{{{name_to_snake(placeholder)}}}"
            )

        normalized_path = re.sub(r"\{[^}]*\}", replace_placeholder, path)
        return normalized_path

    @staticmethod
    def _extract_path_params_from_url(path: str) -> list[BaseParameter]:
        params = []
        path_params = re.findall(r"\{([^}]+)\}", path)

        for param in path_params:
            param_name = name_to_snake(param)
            params.append(
                BaseParameter(
                    name=param_name,
                    type_="str",
                    description=f"Path parameter: {param_name}",
                    required=True,
                )
            )

        return params

    def parse(self) -> list[Handler]:
        info = self.openapi_spec.get("info", {})
        self.version = info.get("version", "1.0.0")
        self.description = info.get("description", "")
        self.openapi_version = self.openapi_spec.get("openapi", "") or self.openapi_spec.get("swagger", "")

        if self.openapi_version.startswith("2."):
            LOGGER.warning(
                "OpenAPI/Swagger version 2.0 is not supported. "
                "You may convert it to 3.0 with https://converter.swagger.io/ "
                "and set the local spec path in 'swagger' option in nuke.toml!"
            )

        paths = self.openapi_spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                self._process_method(path, method, details)
        return self.handlers

    def _process_method(self, path: str, method: str, details: dict) -> None:
        tags = details.get("tags", [])
        for tag in tags:
            self.all_tags.add(tag)

        summary = details.get("summary", "")
        operation_id = details.get("operationId", "")
        parameters = details.get("parameters", [])
        query_parameters = self._get_query_parameters(parameters)
        path_parameters = self._get_path_parameters(parameters)
        headers = self._get_headers(parameters)
        request_body = self._get_request_body(details.get("requestBody", details.get("parameters", {})))
        responses = self._get_response_body(details.get("responses", {}))

        if not path_parameters:
            path_parameters = self._extract_path_params_from_url(path)

        path_obj = Handler(
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
        self.handlers.append(path_obj)

    def request_models(self) -> set[str]:
        models: set[str] = set()
        for handler in self.handlers:
            if handler.request_body is not None:
                models.add(handler.request_body)
        return models

    def response_models(self) -> set[str]:
        models: set[str] = set()
        for handler in self.handlers:
            if handler.responses is not None:
                models.update(handler.responses.values())
        return models

    def models_by_tag(self, tag: str) -> set[str]:
        models: set[str] = set()
        for handler in self.handlers:
            if tag in handler.tags:
                if handler.path_parameters is not None:
                    for param in handler.path_parameters:
                        param_type = param.type
                        if param_type not in TYPE_MAP.values():
                            models.add(param_type)
                if handler.query_parameters is not None:
                    for query_param in handler.query_parameters:
                        query_param_type = query_param.type
                        if query_param_type not in TYPE_MAP.values():
                            models.add(query_param_type)
                if handler.headers is not None:
                    for header_param in handler.headers:
                        header_param_type = header_param.type
                        if header_param_type not in TYPE_MAP.values():
                            models.add(header_param_type)
                if handler.request_body is not None:
                    models.add(handler.request_body)
                if handler.responses is not None:
                    models.update(handler.responses.values())
        return models

    def handlers_by_tag(self, tag: str) -> list[Handler]:
        return [h for h in self.handlers if tag in h.tags]

    def handlers_by_method(self, method: str) -> list[Handler]:
        return [h for h in self.handlers if h.method == method]

    def handler_by_path(self, path: str) -> list[Handler]:
        return [h for h in self.handlers if h.path == path]
