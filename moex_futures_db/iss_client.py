import json
import logging
import time
from collections.abc import Iterable
from typing import Any, Callable

import importlib.util

from moex_futures_db.constants import BASE_URL, COLUMNS_ENDPOINT, SECURITIES_ENDPOINT
from moex_futures_db.httpx_stub import HTTPError, Client

logger = logging.getLogger(__name__)

_HTTPX_SPEC = importlib.util.find_spec("httpx")
if _HTTPX_SPEC is not None:
    import httpx as _httpx

    HTTPError = _httpx.HTTPError
    Client = _httpx.Client


class ISSClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout_s: float = 15.0,
        retries: int = 3,
        backoff_s: float = 0.5,
        page_size: int = 100,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._retries = retries
        self._backoff_s = backoff_s
        self._page_size = page_size
        self._client: Client | None = None

    def __enter__(self) -> "ISSClient":
        self._client = Client(timeout=self._timeout_s)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def fetch_columns(self) -> list[dict[str, Any]]:
        payload = self._request_json(COLUMNS_ENDPOINT, params={"iss.json": "extended"})
        return _find_table(payload, "columns")

    def fetch_securities(self) -> list[dict[str, Any]]:
        def fetch_page(start: int, limit: int) -> list[dict[str, Any]]:
            payload = self._request_json(
                SECURITIES_ENDPOINT,
                params={
                    "start": start,
                    "limit": limit,
                    "iss.json": "extended",
                },
            )
            return _find_table(payload, "securities")

        return list(paginate(fetch_page, self._page_size))

    def _request_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/{path}.json"
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 2):
            try:
                if not self._client:
                    raise RuntimeError("ISSClient must be used as a context manager")
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except (HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "ISS request failed",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "retries": self._retries,
                        "error": str(exc),
                    },
                )
                if attempt <= self._retries:
                    time.sleep(self._backoff_s * attempt)
        raise RuntimeError(f"Failed to fetch {url}") from last_error


def paginate(
    fetch_page: Callable[[int, int], list[dict[str, Any]]],
    page_size: int,
) -> Iterable[dict[str, Any]]:
    start = 0
    while True:
        page = fetch_page(start, page_size)
        if not page:
            return
        for item in page:
            yield item
        start += page_size


def _find_table(payload: dict[str, Any], preferred: str) -> list[dict[str, Any]]:
    if preferred in payload:
        return _parse_table(payload[preferred])
    for key, value in payload.items():
        if isinstance(value, dict) and "columns" in value and "data" in value:
            return _parse_table(value)
    raise ValueError("No table found in ISS response")


def _parse_table(table: dict[str, Any]) -> list[dict[str, Any]]:
    columns = table.get("columns", [])
    data = table.get("data", [])
    return [dict(zip(columns, row, strict=False)) for row in data]
