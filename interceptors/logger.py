from typing import Any, Dict, Union
import httpx
import uuid
import json
import structlog
from json import JSONDecodeError
from curlify2 import Curlify
from urllib.parse import urlparse, parse_qs

from interceptors.protocol import IInterceptor, AsyncIInterceptor


class LoggingInterceptor(IInterceptor):
    def __init__(self) -> None:
        self.log = structlog.get_logger(__name__).bind(service="api")

    def on_request(self, request: httpx.Request) -> httpx.Request:
        log = self.log.bind(event_id=str(uuid.uuid4()))

        try:
            json_data = json.loads(request.content) if request.content else None
        except JSONDecodeError:
            json_data = None

        parsed_url = urlparse(str(request.url))

        msg = {"event": "Request"}
        if request.method:
            msg["method"] = request.method
        if parsed_url.hostname:
            msg["host"] = parsed_url.hostname
        if parsed_url.path:
            msg["path"] = parsed_url.path

        params = parse_qs(parsed_url.query)
        if params:
            msg["params"] = params
        if request.headers:
            msg["headers"] = dict(request.headers)
        if request.content:
            msg["data"] = request.content.decode()
        if isinstance(json_data, dict):
            msg["json"] = json_data
            msg.pop("data", None)

        log.msg(**msg)

        return request

    def on_response(self, response: httpx.Response) -> httpx.Response:
        curl = Curlify(response.request).to_curl()

        self.log.msg(
            event="Response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=self._get_json(response),
            curl=curl,
        )

        return response

    @staticmethod
    def _get_json(response: httpx.Response) -> Union[Dict[str, Any], bytes]:
        try:
            return json.loads(response.read())
        except JSONDecodeError:
            return response.content


class AsyncLoggingInterceptor(AsyncIInterceptor):
    def __init__(self) -> None:
        self.log = structlog.get_logger(__name__).bind(service="api")

    async def on_request(self, request: httpx.Request) -> httpx.Request:
        log = self.log.bind(event_id=str(uuid.uuid4()))

        try:
            json_data = json.loads(request.content) if request.content else None
        except JSONDecodeError:
            json_data = None

        parsed_url = urlparse(str(request.url))

        msg = {"event": "Request"}
        if request.method:
            msg["method"] = request.method
        if parsed_url.hostname:
            msg["host"] = parsed_url.hostname
        if parsed_url.path:
            msg["path"] = parsed_url.path

        params = parse_qs(parsed_url.query)
        if params:
            msg["params"] = params
        if request.headers:
            msg["headers"] = dict(request.headers)
        if request.content:
            msg["data"] = request.content.decode()
        if isinstance(json_data, dict):
            msg["json"] = json_data

        log.msg(**msg)

        return request

    async def on_response(self, response: httpx.Response) -> httpx.Response:
        curl = Curlify(response.request).to_curl()

        self.log.msg(
            event="Response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=await self._get_json(response),
            curl=curl,
        )

        return response

    @staticmethod
    async def _get_json(response: httpx.Response) -> Union[Dict[str, Any], bytes]:
        try:
            return json.loads(await response.aread())
        except JSONDecodeError:
            return response.content
