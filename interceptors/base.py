from typing import Optional

import httpx


class Interceptor:
    def __init__(self, next_interceptor: Optional["Interceptor"] = None):
        self.next_interceptor = next_interceptor

    def intercept(self, request: httpx.Request, client: httpx.Client) -> httpx.Response:
        if self.next_interceptor:
            return self.next_interceptor.intercept(request, client)
        return httpx.Client.send(client, request)
