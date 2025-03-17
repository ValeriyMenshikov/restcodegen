import json
from pathlib import Path
from datamodel_code_generator import DataModelType, generate
from typing import (
    Optional,
)

from restcodegen.generator.base import BaseTemplateGenerator
from restcodegen.generator.log import LOGGER
from restcodegen.generator.parser import OpenAPISpec
from restcodegen.generator.patcher import ClientModelPatcher
from restcodegen.generator.utils import (
    create_and_write_file,
)
from restcodegen.generator.utils import (
    name_to_snake,
)


class RESTClientGenerator(BaseTemplateGenerator):
    BASE_PATH = Path(".") / "clients" / "http"

    def __init__(
        self,
        openapi_spec: OpenAPISpec,
        templates_dir: Optional[Path] = None,
        async_mode: bool = False,
    ) -> None:
        super().__init__(templates_dir=templates_dir)
        self.openapi_spec = openapi_spec
        self.async_mode = async_mode
        self._patcher = ClientModelPatcher(
            models_path=self.BASE_PATH
            / name_to_snake(openapi_spec.service_name)
            / "models"
            / "api_models.py",
            client_path=self.BASE_PATH
            / name_to_snake(openapi_spec.service_name)
            / "apis",
        )

    def generate(self) -> None:
        self._gen_clients()
        self._gen_init_apis()
        self._gen_models()
        self._patcher.patch_client_files()

    def _gen_init_apis(self) -> None:
        LOGGER.info("Generate __init__.py for apis")
        rendered_code = self.env.get_template("apis_init.jinja2").render(
            api_names=self.openapi_spec.apis,
            service_name=self.openapi_spec.service_name,
            version=self.version,
        )
        file_name = f"{name_to_snake(self.openapi_spec.service_name)}/__init__.py"
        file_path = self.BASE_PATH / file_name
        create_and_write_file(file_path=file_path, text=rendered_code)
        create_and_write_file(
            file_path=file_path.parent.parent / "__init__.py", text="# coding: utf-8"
        )

    def _gen_clients(self) -> None:
        for tag in self.openapi_spec.apis:
            LOGGER.info(f"Generate REST client for tag: {tag}")
            handlers = self.openapi_spec.handlers_by_tag(tag)
            models = self.openapi_spec.models_by_tag(tag)
            rendered_code = self.env.get_template("api_client.jinja2").render(
                async_mode=self.async_mode,
                models=models,
                data_list=handlers,
                api_name=tag,
                service_name=self.openapi_spec.service_name,
                version=self.version,
            )
            file_name = f"{name_to_snake(tag)}_api.py"
            file_path = (
                self.BASE_PATH
                / name_to_snake(self.openapi_spec.service_name)
                / "apis"
                / file_name
            )
            create_and_write_file(file_path=file_path, text=rendered_code)
            create_and_write_file(
                file_path=file_path.parent / "__init__.py", text="# coding: utf-8"
            )

    def _gen_models(self) -> None:
        LOGGER.info(f"Generate models for service: {self.openapi_spec.service_name}")
        file_path = (
            self.BASE_PATH
            / name_to_snake(self.openapi_spec.service_name)
            / "models"
            / "api_models.py"
        )
        create_and_write_file(file_path=file_path)
        create_and_write_file(
            file_path=file_path.parent / "__init__.py", text="# coding: utf-8"
        )
        header_path_template = self.templates_dir / "header.jinja2"
        generate(
            json.dumps(self.openapi_spec.openapi_spec),
            output=file_path,
            snake_case_field=True,
            output_model_type=DataModelType.PydanticV2BaseModel,
            reuse_model=True,
            field_constraints=True,
            custom_file_header_path=header_path_template,
            capitalise_enum_members=True,
            encoding="utf-8",
            use_title_as_name=True,
        )
