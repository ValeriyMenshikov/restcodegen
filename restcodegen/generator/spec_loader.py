import json
from pathlib import Path
from typing import Union
from pydantic import HttpUrl
import httpx

from restcodegen.generator.log import LOGGER
from restcodegen.generator.spec_patcher import SpecPatcher
from restcodegen.generator.utils import name_to_snake


class SpecLoader:
    BASE_PATH = Path.cwd() / "clients" / "http"

    def __init__(self, spec: str, service_name: str) -> None:
        self.spec_path = spec
        self.service_name = service_name
        self.cache_spec_dir = self.BASE_PATH / "schemas"

        if not self.cache_spec_dir.exists():
            self.cache_spec_dir.mkdir(parents=True, exist_ok=True)

        self.cache_spec_path = (
            self.cache_spec_dir / f"{name_to_snake(self.service_name)}.json"
        )
        self._patcher = SpecPatcher()

    def _get_spec_by_url(self) -> Union[dict, None]:
        try:
            response = httpx.get(self.spec_path, timeout=5)
            response.raise_for_status()
        except httpx.HTTPError:
            spec = {}
            LOGGER.warning(f"OpenAPI spec not available by url: {self.spec_path} ")
            file_path = (
                self.spec_path
                if Path(self.spec_path).is_file()
                else str(self.cache_spec_path)
            )
            if Path(file_path).is_file():
                LOGGER.warning(f"Try open OpenAPI spec by path: {file_path}")
                with open(file_path, "r") as f:
                    spec = self._patcher.patch(json.loads(f.read()))
            return spec
        else:
            spec = self._patcher.patch(response.json())
            with open(self.cache_spec_path, "w") as f:
                f.write(json.dumps(spec, indent=4, ensure_ascii=False))
            return spec

    def _get_spec_from_cache(self) -> dict:
        try:
            with open(self.cache_spec_path, "r") as f:
                spec = self._patcher.patch(json.loads(f.read()))
                self.spec_path = self.cache_spec_path  # type: ignore
                LOGGER.warning(f"OpenAPI spec got from cash: {self.spec_path}")
                return spec
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"OpenAPI spec not available from url: {self.spec_path}, and not found in cash"
            ) from e

    def _get_spec_by_path(self) -> Union[dict, None]:
        try:
            with open(self.spec_path, "r") as f:
                spec = json.loads(f.read())
        except FileNotFoundError:
            LOGGER.warning(f"OpenAPI spec not found from local path: {self.spec_path}")
            return None
        else:
            return spec

    def open(self) -> dict:
        spec = self._get_spec_by_url()
        if not spec:
            spec = self._get_spec_by_path()
        if not spec:
            spec = self._get_spec_from_cache()
        return spec
