from httpx import URL
from typing import Any


class Configuration:
    def __init__(
        self, *, base_url: URL | str = "", disable_log: bool = False, **kwargs: Any
    ):
        """
        Parameters:
            base_url (optional):
                A URL to use as the base when building request URLs.

            disable_log (bool, optional):
                Disables logging if set to True. Defaults to False.

            auth (optional):
                An authentication class to use when sending requests.

            params (optional):
                Query parameters to include in request URLs, as a string, dictionary,
                or sequence of two-tuples.

            headers (optional):
                Dictionary of HTTP headers to include when sending requests.

            cookies (optional):
                Dictionary of Cookie items to include when sending requests.

            verify (optional):
                Either `True` to use an SSL context with the default CA bundle,
                `False` to disable verification, or an instance of `ssl.SSLContext`
                to use a custom context.

            http2 (optional):
                A boolean indicating if HTTP/2 support should be enabled. Defaults to `False`.

            proxy (optional):
                A proxy URL where all the traffic should be routed.

            timeout (optional):
                The timeout configuration to use when sending requests.

            limits (optional):
                The limits configuration to use.

            max_redirects (optional):
                The maximum number of redirect responses that should be followed.

            transport (optional):
                A transport class to use for sending requests over the network.

            trust_env (optional):
                Enables or disables usage of environment variables for configuration.

            default_encoding (optional):
                The default encoding to use for decoding response text, if no charset
                information is included in a response Content-Type header. Set to a
                callable for automatic character set detection. Default: "utf-8".

        """
        self.base_url = base_url
        self.disable_log = disable_log
        self.kwargs = kwargs
