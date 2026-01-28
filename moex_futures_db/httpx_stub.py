import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HTTPError(Exception):
    pass


class Response:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self._content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return json.loads(self._content.decode("utf-8"))


class Client:
    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    def close(self) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None) -> Response:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return Response(response.status, response.read())
        except urllib.error.HTTPError as exc:
            return Response(exc.code, exc.read())
        except urllib.error.URLError as exc:
            raise HTTPError(str(exc)) from exc
