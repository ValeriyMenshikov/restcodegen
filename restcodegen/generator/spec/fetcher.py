from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class SpecFetchError(RuntimeError):
    """Raised when удалённую спецификацию не удалось получить."""


@dataclass(slots=True)
class FetchSettings:
    timeout: float = 60.0
    verify_ssl: bool = True


class SpecFetcher:
    """Отвечает только за загрузку спецификации по сети."""

    def __init__(self, settings: FetchSettings | None = None) -> None:
        self._settings = settings or FetchSettings()

    def fetch(self, url: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self._settings.timeout, verify=self._settings.verify_ssl) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - httpx already протестирован
            raise SpecFetchError(f"Не удалось получить спецификацию по адресу {url!r}") from exc
