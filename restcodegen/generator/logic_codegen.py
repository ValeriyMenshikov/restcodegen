from pathlib import Path

from restcodegen.generator.base import BaseTemplateGenerator
from restcodegen.generator.log import LOGGER
from restcodegen.generator.parser import OpenAPISpec
from restcodegen.generator.utils import name_to_snake, create_and_write_file


class LogicGenerator(BaseTemplateGenerator):
    BASE_PATH = Path(".") / "helpers"

    def __init__(
        self,
        openapi_spec: OpenAPISpec,
        async_mode: bool = False,
    ):
        super().__init__()
        self.openapi_spec = openapi_spec
        self.path = (
            self.BASE_PATH
            / openapi_spec.client_type
            / name_to_snake(openapi_spec.service_name)
        )
        self.async_mode = async_mode

    def generate(self):
        self._gen_client_wrappers()
        self._gen_facade()
        self._gen_logic_facade()

    def _gen_client_wrappers(self):
        for tag in self.openapi_spec.apis:
            LOGGER.info(f"Generate client logic for: {tag}")
            # TODO сделать чтобы для не target сервисов при добавлении одного метода не добавлялись остальные
            models = self.openapi_spec.models_by_tag(tag)
            service_name = self.openapi_spec.service_name
            rendered_code = self.env.get_template("api_helper.jinja2").render(
                models=models,
                api_name=tag,
                service_name=service_name,
            )
            file_name = f"{name_to_snake(tag)}_helper.py"
            file_path = self.path / file_name
            if file_path.exists():
                LOGGER.info(
                    f"File: {file_path} exists but it's not target service, skip generate!"
                )
            else:
                create_and_write_file(file_path=file_path, text=rendered_code)

    def _gen_facade(self):
        LOGGER.info(
            f"Generate wrapper facade for service: {self.openapi_spec.service_name}"
        )
        rendered_code = self.env.get_template("service_facade.jinja2").render(
            client_type=self.openapi_spec.client_type,
            api_names=self.openapi_spec.apis,
            service_name=self.openapi_spec.service_name,
        )
        file_name = f"__init__.py"
        file_path = self.path / file_name
        create_and_write_file(file_path=file_path, text=rendered_code)

    def _gen_logic_facade(self):
        LOGGER.info(
            f"Generate logic facade for service: {self.openapi_spec.service_name}"
        )
        rendered_code = self.env.get_template("service_helper.jinja2").render(
            client_type=self.openapi_spec.client_type,
            api_names=self.openapi_spec.apis,
            service_name=self.openapi_spec.service_name,
        )
        service_name = name_to_snake(self.openapi_spec.service_name)
        file_name = f"{service_name}.py"
        file_path = self.path.parent / file_name
        if file_path.exists():
            LOGGER.warning(f"File: {file_path} exists, skip generate!")
            return
        create_and_write_file(file_path=file_path, text=rendered_code)
