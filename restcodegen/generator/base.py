import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from restcodegen.generator import TEMPLATES
from restcodegen.generator.log import LOGGER
from restcodegen.generator.utils import name_to_snake, snake_to_camel, get_version, rename_python_builtins


class BaseGenerator:
    """Base generator class providing common functionality for all generators."""
    BASE_PATH: Path

    def __init__(self) -> None:
        """Initialize the generator and create necessary directory structure."""
        if not self.BASE_PATH.exists():
            LOGGER.debug("Base directory does not exist, creating...")
            self.BASE_PATH.mkdir(parents=True)

        self._create_init_files()

    def _create_init_files(self) -> None:
        """Create necessary __init__.py files."""
        core_init_path = self.BASE_PATH / "__init__.py"
        if not core_init_path.exists():
            core_init_path.touch()

        if not (self.BASE_PATH.parent / "__init__.py").exists():
            (self.BASE_PATH.parent / "__init__.py").touch()

    def __del__(self) -> None:
        """Removes empty directories."""
        if hasattr(self, 'BASE_PATH') and self.BASE_PATH.exists():
            files_count = sum(1 for _ in self.BASE_PATH.glob("*"))
            if files_count == 1:
                shutil.rmtree(self.BASE_PATH)


class BaseTemplateGenerator(BaseGenerator):
    """Base template generator providing Jinja2 templating capabilities."""
    
    def __init__(self, templates_dir: Path | None = None):
        """Initialize the template generator with Jinja2 environment.
        
        Args:
            templates_dir: Optional custom templates directory path
        """
        super().__init__()
        self.templates_dir = templates_dir or TEMPLATES
        self.version = get_version()
        self.env = self._create_jinja_environment()
        
    def _create_jinja_environment(self) -> Environment:
        """Create and configure Jinja2 environment with custom filters.
        
        Returns:
            Configured Jinja2 Environment
        """
        env = Environment(
            loader=FileSystemLoader(self.templates_dir), 
            autoescape=True
        )  # type: ignore
        
        # Register custom filters
        env.filters["to_snake_case"] = name_to_snake
        env.filters["to_camel_case"] = snake_to_camel
        env.filters["rename_python_builtins"] = rename_python_builtins
        
        return env
