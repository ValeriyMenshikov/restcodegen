from json import JSONDecodeError
from urllib.parse import urlparse, parse_qs

import httpx
import json
import allure
from curlify2 import Curlify

from interceptors.protocol import IInterceptor, AsyncIInterceptor


class AsyncAllureInterceptor(AsyncIInterceptor):
    async def on_request(self, request: httpx.Request) -> httpx.Request:
        try:
            json_data = json.loads(request.content) if request.content else None
        except JSONDecodeError:
            json_data = None

        parsed_url = urlparse(str(request.url))

        request_params = {"event": "Request"}
        if request.method:
            request_params["method"] = request.method
        if parsed_url.hostname:
            request_params["host"] = parsed_url.hostname
        if parsed_url.path:
            request_params["path"] = parsed_url.path

        if params := parse_qs(parsed_url.query):
            request_params["params"] = params
        if request.headers:
            request_params["headers"] = dict(request.headers)
        if request.content:
            request_params["data"] = request.content.decode()
        if isinstance(json_data, dict):
            request_params["json"] = json_data

        with allure.step(f"{request.method} {parsed_url.path}"):
            allure.attach(
                json.dumps(request_params, indent=4),
                name="request_body",
                attachment_type=allure.attachment_type.JSON,
            )
        return request

    async def on_response(self, response: httpx.Response) -> httpx.Response:
        curl = Curlify(response.request).to_curl()
        allure.attach(curl, name="curl", attachment_type=allure.attachment_type.TEXT)

        try:
            response_json = json.loads(await response.aread())
            allure.attach(
                json.dumps(response_json, indent=4),
                name="response_body",
                attachment_type=allure.attachment_type.JSON,
            )
        except json.JSONDecodeError:
            response_text = response.text
            status_code = f"status code = {response.status_code}"
            allure.attach(
                response_text if len(response_text) > 0 else status_code,
                name="response_body",
                attachment_type=allure.attachment_type.TEXT,
            )

        return response


class AllureInterceptor(IInterceptor):
    def on_request(self, request: httpx.Request) -> httpx.Request:
        try:
            json_data = json.loads(request.content) if request.content else None
        except JSONDecodeError:
            json_data = None

        parsed_url = urlparse(str(request.url))

        request_params = {"event": "Request"}
        if request.method:
            request_params["method"] = request.method
        if parsed_url.hostname:
            request_params["host"] = parsed_url.hostname
        if parsed_url.path:
            request_params["path"] = parsed_url.path

        if params := parse_qs(parsed_url.query):
            request_params["params"] = params
        if request.headers:
            request_params["headers"] = dict(request.headers)
        if request.content:
            request_params["data"] = request.content.decode()
        if isinstance(json_data, dict):
            request_params["json"] = json_data

        with allure.step(f"{request.method} {parsed_url.path}"):
            allure.attach(
                json.dumps(request_params, indent=4),
                name="request_body",
                attachment_type=allure.attachment_type.JSON,
            )
        return request

    def on_response(self, response: httpx.Response) -> httpx.Response:
        curl = Curlify(response.request).to_curl()
        allure.attach(curl, name="curl", attachment_type=allure.attachment_type.TEXT)

        try:
            response_json = json.loads(response.read())
            allure.attach(
                json.dumps(response_json, indent=4),
                name="response_body",
                attachment_type=allure.attachment_type.JSON,
            )
        except json.JSONDecodeError:
            response_text = response.text
            status_code = f"status code = {response.status_code}"
            allure.attach(
                response_text if len(response_text) > 0 else status_code,
                name="response_body",
                attachment_type=allure.attachment_type.TEXT,
            )

        return response
