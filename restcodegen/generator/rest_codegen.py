import json
from functools import cached_property
from pathlib import Path

from datamodel_code_generator import DataModelType, generate

from restcodegen.generator.base import BaseTemplateGenerator
from restcodegen.generator.log import LOGGER
from restcodegen.generator.parser import Parser, Handler
from restcodegen.generator.utils import (
    create_and_write_file,
    name_to_snake,
)


class RESTClientGenerator(BaseTemplateGenerator):
    BASE_PATH = Path(".") / "clients" / "http"

    def __init__(
        self,
        openapi_spec: Parser,
        templates_dir: str | None = None,
        async_mode: bool = False,
        base_path: str | Path | None = None,
    ) -> None:
        super().__init__(templates_dir=templates_dir)
        self.openapi_spec = openapi_spec
        self.async_mode = async_mode
        self.base_path = Path(base_path) if base_path is not None else self.BASE_PATH

    @cached_property
    def _base_import(self) -> str:
        base = self.base_path
        if base.is_absolute():
            try:
                base = base.relative_to(Path.cwd())
            except ValueError:
                pass
        return ".".join(list(base.parts))

    def generate(self) -> None:
        self._gen_clients()
        self._gen_init_apis()
        self._gen_models()

    def _gen_init_apis(self) -> None:
        LOGGER.info("Generate __init__.py for apis")
        rendered_code = self.env.get_template("apis_init.jinja2").render(
            api_names=self.openapi_spec.apis,
            service_name=self.openapi_spec.service_name,
            version=self.version,
            base_import=self._base_import,
        )
        file_name = f"{name_to_snake(self.openapi_spec.service_name)}/__init__.py"
        file_path = self.base_path / file_name
        create_and_write_file(file_path=file_path, text=rendered_code)
        create_and_write_file(file_path=file_path.parent.parent / "__init__.py", text="# coding: utf-8")

    def _gen_clients(self) -> None:
        for tag in self.openapi_spec.apis:
            LOGGER.info(f"Generate REST client for tag: {tag}")
            handlers = [self._prepare_handler(handler) for handler in self.openapi_spec.handlers_by_tag(tag)]
            models = self.openapi_spec.models_by_tag(tag)
            rendered_code = self.env.get_template("api_client.jinja2").render(
                async_mode=self.async_mode,
                models=models,
                data_list=handlers,
                api_name=tag,
                service_name=self.openapi_spec.service_name,
                version=self.version,
                base_import=self._base_import,
            )
            file_name = f"{name_to_snake(tag)}_api.py"
            file_path = self.base_path / name_to_snake(self.openapi_spec.service_name) / "apis" / file_name
            create_and_write_file(file_path=file_path, text=rendered_code)
            create_and_write_file(file_path=file_path.parent / "__init__.py", text="# coding: utf-8")

    @staticmethod
    def _prepare_handler(handler: Handler) -> Handler:
        for attribute in ("path_parameters", "query_parameters", "headers"):
            params = handler.get(attribute)
            if params:
                sorted_params = sorted(params, key=lambda p: not p.required)
                setattr(handler, attribute, sorted_params)
            else:
                setattr(handler, attribute, [])
        return handler

    def _gen_models(self) -> None:
        LOGGER.info(f"Generate models for service: {self.openapi_spec.service_name}")
        file_path = self.base_path / name_to_snake(self.openapi_spec.service_name) / "models" / "api_models.py"
        create_and_write_file(file_path=file_path)
        create_and_write_file(file_path=file_path.parent / "__init__.py", text="# coding: utf-8")
        header_path_template = self.templates_dir / "header.jinja2"
        generate(
            json.dumps(self.openapi_spec.openapi_spec),
            output=file_path,
            snake_case_field=True,
            output_model_type=DataModelType.PydanticV2BaseModel,
            reuse_model=False,
            field_constraints=True,
            custom_file_header_path=header_path_template,
            capitalise_enum_members=True,
            encoding="utf-8",
        )
