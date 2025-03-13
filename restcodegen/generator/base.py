import shutil
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from restcodegen.generator import TEMPLATES
from restcodegen.generator.log import LOGGER
from restcodegen.generator.utils import name_to_snake, snake_to_camel, get_version


class BaseGenerator:
    BASE_PATH: Path

    def __init__(self) -> None:
        if not self.BASE_PATH.exists():
            LOGGER.debug("base directory does not exists, creating...")
            self.BASE_PATH.mkdir(parents=True)

        core_init_path = self.BASE_PATH / "__init__.py"
        if not core_init_path.exists():
            core_init_path.touch()

        if not (self.BASE_PATH.parent / "__init__.py").exists():
            (self.BASE_PATH.parent / "__init__.py").touch()

    def __del__(self) -> None:
        """Removes empty directories."""
        files_count = sum(1 for _ in self.BASE_PATH.glob("*"))
        if files_count == 1:
            shutil.rmtree(self.BASE_PATH)


class BaseTemplateGenerator(BaseGenerator):
    def __init__(self, templates_dir: Optional[Path] = None):
        super().__init__()
        self.templates_dir = templates_dir or TEMPLATES
        self.version = get_version()
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir), autoescape=True
        )  # type: ignore
        self.env.filters["to_snake_case"] = name_to_snake
        self.env.filters["to_camel_case"] = snake_to_camel
