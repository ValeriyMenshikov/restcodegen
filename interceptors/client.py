import httpx
from typing import Optional

from interceptors.allure import AllureAttachInterceptor
from interceptors.base import Interceptor
from interceptors.logging import LoggingInterceptor


class Client(httpx.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interceptor_chain: Optional[Interceptor] = None

    def add_interceptor(self, interceptor: Interceptor):
        if self.interceptor_chain is None:
            self.interceptor_chain = interceptor
        else:
            last_interceptor = self.interceptor_chain
            while last_interceptor.next_interceptor:
                last_interceptor = last_interceptor.next_interceptor
            last_interceptor.next_interceptor = interceptor

    def send(self, request: httpx.Request, **kwargs) -> httpx.Response:
        if self.interceptor_chain:
            return self.interceptor_chain.intercept(request, self)
        return super().send(request, **kwargs)


# Пример использования
def main():
    client = Client()
    client.add_interceptor(LoggingInterceptor())
    client.add_interceptor(AllureAttachInterceptor())

    response = client.get("https://httpbin.org/get")


# Запуск синхронного кода
if __name__ == "__main__":
    main()
