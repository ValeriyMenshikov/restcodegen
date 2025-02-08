from typing import Any

import httpx
from json.decoder import JSONDecodeError
import structlog
import uuid
from curlify2 import Curlify


from restcodegen.rest_client.configuration import Configuration


class ApiClient:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.host = self.configuration.host
        self.set_headers(self.configuration.headers)
        self.disable_log = self.configuration.disable_log
        self.session = httpx.Client(base_url=self.host)
        self.log = structlog.get_logger(__name__).bind(service="api")

    def set_headers(self, headers: dict | None) -> None:
        if headers:
            self.session.headers.update(headers)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="POST", path=path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="GET", path=path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="PUT", path=path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="DELETE", path=path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="PATCH", path=path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="OPTIONS", path=path, **kwargs)

    def head(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._send_request(method="HEAD", path=path, **kwargs)

    def _send_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        log = self.log.bind(event_id=str(uuid.uuid4()))

        if self.disable_log:
            rest_response = self.session.request(method=method, url=path, **kwargs)
            rest_response.raise_for_status()
            return rest_response

        log.msg(
            event="Request",
            method=method,
            path=path,
            host=self.host,
            params=kwargs.get("params"),
            headers=kwargs.get("headers"),
            json=kwargs.get("json"),
            data=kwargs.get("data"),
        )
        rest_response = self.session.request(method=method, url=path, **kwargs)

        curl = Curlify(rest_response.request).to_curl()
        print(curl)
        log.msg(
            event="Response",
            status_code=rest_response.status_code,
            headers=rest_response.headers,
            json=self._get_json(rest_response),
        )
        rest_response.raise_for_status()
        return rest_response

    @staticmethod
    def _get_json(rest_response: httpx.Response) -> dict:
        try:
            return rest_response.json()
        except JSONDecodeError:
            return {}
