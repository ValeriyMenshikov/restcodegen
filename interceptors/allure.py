import json
import allure
import curlify2
import httpx
from typing import Optional

from interceptors.base import Interceptor


class AllureAttachInterceptor:
    def __init__(self, next_interceptor: Optional["Interceptor"] = None):
        self.next_interceptor = next_interceptor

    def intercept(self, request: httpx.Request, client: httpx.Client) -> httpx.Response:
        if request.content:
            try:
                request_body = json.loads(request.content)
                allure.attach(
                    json.dumps(request_body, indent=4),
                    name="request_body",
                    attachment_type=allure.attachment_type.JSON,
                )
            except json.JSONDecodeError:
                allure.attach(
                    request.content.decode("utf-8"),
                    name="request_body",
                    attachment_type=allure.attachment_type.TEXT,
                )

        if self.next_interceptor:
            response = self.next_interceptor.intercept(request, client)
        else:
            response = httpx.Client.send(client, request)

        curl = curlify2.Curlify(request).to_curl()
        allure.attach(curl, name="curl", attachment_type=allure.attachment_type.TEXT)

        try:
            response_json = response.json()
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
