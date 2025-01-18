from typing import Optional


class Configuration:
    def __init__(
        self,
        host: str,
        headers: Optional[dict] = None,
        disable_log: Optional[bool] = True,
    ):
        self.host = host
        self.headers = headers
        self.disable_log = disable_log
