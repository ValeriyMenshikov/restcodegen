from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from restcodegen.generator.log import LOGGER
from restcodegen.generator.spec.fetcher import FetchSettings, SpecFetcher, SpecFetchError
from restcodegen.generator.spec.normalizer import SpecNormalizer
from restcodegen.generator.utils import is_url, name_to_snake


class SpecLoader:
    BASE_PATH = Path.cwd() / "clients" / "http"

    def __init__(
        self,
        spec: str,
        service_name: str,
        *,
        fetcher: SpecFetcher | None = None,
        normalizer: SpecNormalizer | None = None,
        fetch_settings: FetchSettings | None = None,
    ) -> None:
        self.spec_path = spec
        self.service_name = service_name
        self.cache_spec_dir = self.BASE_PATH / "schemas"

        if not self.cache_spec_dir.exists():
            self.cache_spec_dir.mkdir(parents=True, exist_ok=True)

        self.cache_spec_path = self.cache_spec_dir / f"{name_to_snake(self.service_name)}.json"
        self._fetcher = fetcher or SpecFetcher(settings=fetch_settings)
        self._normalizer = normalizer or SpecNormalizer()

    def _get_spec_by_url(self) -> dict[str, Any] | None:
        if not is_url(self.spec_path):
            return None

        try:
            spec = self._fetcher.fetch(self.spec_path)
        except SpecFetchError as exc:
            LOGGER.warning("OpenAPI spec not available by url %s: %s", self.spec_path, exc)
            return None

        self._write_cache(spec)
        return spec

    def _get_spec_from_cache(self) -> dict[str, Any]:
        try:
            with open(self.cache_spec_path) as f:
                spec = json.loads(f.read())
                self.spec_path = self.cache_spec_path  # type: ignore
                LOGGER.warning("OpenAPI spec loaded from cache: %s", self.spec_path)
                return spec
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"OpenAPI spec not available from url: {self.spec_path}, and not found in cache"
            ) from e

    def _get_spec_by_path(self) -> dict[str, Any] | None:
        try:
            with open(self.spec_path) as f:
                spec = json.loads(f.read())
        except FileNotFoundError:
            LOGGER.warning("OpenAPI spec not found from local path: %s", self.spec_path)
            return None
        else:
            return spec

    def _write_cache(self, spec: dict[str, Any]) -> None:
        try:
            with open(self.cache_spec_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(spec, indent=4, ensure_ascii=False))
        except OSError as exc:
            LOGGER.warning("Unable to write cache file %s: %s", self.cache_spec_path, exc)

    def open(self) -> dict[str, Any]:
        spec: dict[str, Any] | None = self._get_spec_by_url()
        if spec is None:
            spec = self._get_spec_by_path()
        if spec is None:
            spec = self._get_spec_from_cache()

        return self._normalizer.normalize(spec)
