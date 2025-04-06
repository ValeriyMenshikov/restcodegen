import httpx
from typing import Protocol, runtime_checkable


@runtime_checkable
class IInterceptor(Protocol):
    def on_request(self, request: httpx.Request) -> httpx.Request: ...

    def on_response(self, response: httpx.Response) -> httpx.Response: ...


@runtime_checkable
class AsyncIInterceptor(Protocol):
    async def on_request(self, request: httpx.Request) -> httpx.Request: ...
    async def on_response(self, response: httpx.Response) -> httpx.Response: ...


def wrap_interceptors(interceptors: list[IInterceptor | AsyncIInterceptor]) -> dict:
    return {
        "request": [i.on_request for i in interceptors],
        "response": [i.on_response for i in interceptors],
    }
