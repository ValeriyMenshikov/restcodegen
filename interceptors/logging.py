import json
import uuid
from typing import Optional, Any, Dict, Union
import httpx
import structlog
from curlify2 import Curlify

from interceptors.base import Interceptor


class LoggingInterceptor:
    def __init__(self, next_interceptor: Optional["Interceptor"] = None):
        self.next_interceptor = next_interceptor
        self.log = structlog.get_logger(__name__).bind(service="api")

    def intercept(self, request: httpx.Request, client: httpx.Client) -> httpx.Response:
        self.log_request(
            request.method, str(request.url), **self._extract_request_data(request)
        )

        if self.next_interceptor:
            response = self.next_interceptor.intercept(request, client)
        else:
            response = httpx.Client.send(client, request)

        self.log_response(response)
        return response

    def log_request(self, method: str, url: str, **kwargs: Any) -> None:
        log = self.log.bind(event_id=str(uuid.uuid4()))
        json_data = kwargs.get("json")
        content = kwargs.get("content")

        try:
            if content:
                json_data = json.loads(content)
        except json.JSONDecodeError:
            pass

        msg = {
            "event": "Request",
            "method": method,
            "path": url,
            "params": kwargs.get("params"),
            "headers": kwargs.get("headers"),
            "data": kwargs.get("data"),
        }

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
    def _get_json(response: httpx.Response) -> Union[Dict[str, Any], bytes]:
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.content

    @staticmethod
    def _extract_request_data(request: httpx.Request) -> Dict[str, Any]:
        return {
            "json": request.headers.get("Content-Type") == "application/json"
            and request.content,
            "content": request.content,
            "params": request.url.params,
            "headers": dict(request.headers),
            "data": request.content,
        }
