from typing import Any
import json
import httpx
from json.decoder import JSONDecodeError
import structlog
import uuid
from curlify2 import Curlify

from restcodegen.restclient.configuration import Configuration


class Logging:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        self.log = structlog.get_logger(__name__).bind(service="api")

    def log_request(self, method: str, url: str, **kwargs: Any) -> None:
        log = self.log.bind(event_id=str(uuid.uuid4()))
        json_data = kwargs.get("json")
        content = kwargs.get("content")
        try:
            if content:
                json_data = json.loads(content)
        except JSONDecodeError:
            ...

        msg = dict(
            event="Request",
            method=method,
            path=url,
            host=self.configuration.base_url,
            params=kwargs.get("params"),
            headers=kwargs.get("headers"),
            data=kwargs.get("data"),
        )

        if isinstance(json_data, dict):
            msg["json"] = json_data

        log.msg(**msg)

    def log_response(self, response: httpx.Response) -> None:
        log = self.log.bind(event_id=str(uuid.uuid4()))
        curl = Curlify(response.request).to_curl()
        print(curl)
        log.msg(
            event="Response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=self._get_json(response),
        )

    @staticmethod
    def _get_json(response: httpx.Response) -> dict[str, Any] | bytes:
        try:
            return response.json()
        except JSONDecodeError:
            return response.content


class Client(httpx.Client):
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        super().__init__(
            base_url=self.configuration.base_url, **self.configuration.kwargs
        )
        self._logger = Logging(self.configuration)

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:  # type: ignore
        if not self.configuration.disable_log:
            self._logger.log_request(method, url, **kwargs)

        response = super().request(method, url, **kwargs)

        if not self.configuration.disable_log:
            self._logger.log_response(response)

        response.raise_for_status()
        return response


class AsyncClient(httpx.AsyncClient):
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        super().__init__(
            base_url=self.configuration.base_url, **self.configuration.kwargs
        )
        self._logger = Logging(configuration)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:  # type: ignore
        if not self.configuration.disable_log:
            self._logger.log_request(method, url, **kwargs)

        response = await super().request(method, url, **kwargs)

        if not self.configuration.disable_log:
            self._logger.log_response(response)

        response.raise_for_status()
        return response
