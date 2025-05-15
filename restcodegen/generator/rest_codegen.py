import json
from pathlib import Path

from datamodel_code_generator import DataModelType, generate

from restcodegen.generator.base import BaseTemplateGenerator
from restcodegen.generator.log import LOGGER
from restcodegen.generator.parser import OpenAPISpec, Handler
from restcodegen.generator.patcher import ClientModelPatcher
from restcodegen.generator.utils import create_and_write_file, name_to_snake


class RESTClientGenerator(BaseTemplateGenerator):
    """Generator for REST API clients based on OpenAPI specifications."""
    
    BASE_PATH = Path(".") / "clients" / "http"

    def __init__(
        self,
        openapi_spec: OpenAPISpec,
        templates_dir: Path | None = None,
        async_mode: bool = False,
    ) -> None:
        """Initialize the REST client generator.
        
        Args:
            openapi_spec: Parsed OpenAPI specification
            templates_dir: Optional custom templates directory
            async_mode: Whether to generate async client code
        """
        super().__init__(templates_dir=templates_dir)
        self.openapi_spec = openapi_spec
        self.async_mode = async_mode
        self._patcher = self._create_patcher()
        
    def _create_patcher(self) -> ClientModelPatcher:
        """Create a model patcher for the generated client.
        
        Returns:
            Configured ClientModelPatcher instance
        """
        service_name_snake = name_to_snake(self.openapi_spec.service_name)
        return ClientModelPatcher(
            models_path=self.BASE_PATH / service_name_snake / "models" / "api_models.py",
            client_path=self.BASE_PATH / service_name_snake / "apis",
        )

    def generate(self) -> None:
        """Generate all components of the REST client."""
        LOGGER.info(f"Generating REST client for service: {self.openapi_spec.service_name}")
        self._gen_clients()
        self._gen_init_apis()
        self._gen_models()
        self._patcher.patch_client_files()
        LOGGER.info(f"REST client generation completed for: {self.openapi_spec.service_name}")

    def _gen_init_apis(self) -> None:
        """Generate __init__.py file for the APIs package."""
        LOGGER.info("Generating __init__.py for APIs")
        service_name_snake = name_to_snake(self.openapi_spec.service_name)
        
        rendered_code = self.env.get_template("apis_init.jinja2").render(
            api_names=self.openapi_spec.apis,
            service_name=self.openapi_spec.service_name,
            version=self.version,
        )
        
        file_name = f"{service_name_snake}/__init__.py"
        file_path = self.BASE_PATH / file_name
        create_and_write_file(file_path=file_path, text=rendered_code)
        
        # Create parent __init__.py
        create_and_write_file(
            file_path=file_path.parent.parent / "__init__.py", 
            text="# coding: utf-8"
        )

    def _gen_clients(self) -> None:
        """Generate client API files for each API tag."""
        service_name_snake = name_to_snake(self.openapi_spec.service_name)
        
        for tag in self.openapi_spec.apis:
            LOGGER.info(f"Generating REST client for tag: {tag}")
            self._gen_client_for_tag(tag, service_name_snake)
            
    def _gen_client_for_tag(self, tag: str, service_name_snake: str) -> None:
        """Generate client API file for a specific tag.
        
        Args:
            tag: API tag to generate client for
            service_name_snake: Snake-cased service name
        """
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
        
        # Create API file
        file_name = f"{name_to_snake(tag)}_api.py"
        file_path = self.BASE_PATH / service_name_snake / "apis" / file_name
        create_and_write_file(file_path=file_path, text=rendered_code)
        
        # Create __init__.py if needed
        init_path = file_path.parent / "__init__.py"
        if not init_path.exists():
            create_and_write_file(file_path=init_path, text="# coding: utf-8")

    def _gen_models(self) -> None:
        """Generate model files based on OpenAPI schemas."""
        LOGGER.info(f"Generating models for service: {self.openapi_spec.service_name}")
        service_name_snake = name_to_snake(self.openapi_spec.service_name)
        
        # Create model directory and files
        models_dir = self.BASE_PATH / service_name_snake / "models"
        file_path = models_dir / "api_models.py"
        
        # Ensure directory exists
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Create empty file for models
        create_and_write_file(file_path=file_path)
        
        # Create __init__.py if needed
        init_path = models_dir / "__init__.py"
        if not init_path.exists():
            create_and_write_file(file_path=init_path, text="# coding: utf-8")
        
        # Generate models using datamodel-code-generator
        header_path_template = self.templates_dir / "header.jinja2"
        self._generate_models_with_datamodel_generator(file_path, header_path_template)
    
    def _generate_models_with_datamodel_generator(self, file_path: Path, header_path_template: Path) -> None:
        """Generate models using datamodel-code-generator.
        
        Args:
            file_path: Path to write models to
            header_path_template: Template for file header
        """
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
        )
