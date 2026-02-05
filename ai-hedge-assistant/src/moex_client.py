from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests


LOGGER = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    expires_at: float
    payload: Dict[str, Any]


class MoexClient:
    def __init__(
        self,
        base_url: str = "https://iss.moex.com",
        timeout: float = 8.0,
        retries: int = 3,
        cache_ttl: int = 45,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self._cache: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], CacheEntry] = {}

    def _cache_key(self, url: str, params: Optional[Dict[str, Any]]) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
        items = tuple(sorted((params or {}).items()))
        return url, items

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        key = self._cache_key(url, params)
        now = time.time()

        if key in self._cache and self._cache[key].expires_at > now:
            return self._cache[key].payload

        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                self._cache[key] = CacheEntry(expires_at=now + self.cache_ttl, payload=payload)
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                LOGGER.warning("MOEX ISS request failed on attempt %s/%s: %s", attempt, self.retries, exc)
                time.sleep(0.5 * attempt)

        raise RuntimeError(f"MOEX ISS request failed after {self.retries} attempts: {last_error}")

    def get_futures_list(self) -> Dict[str, Any]:
        return self._get_json(
            "/iss/engines/futures/markets/forts/boards/rfud/securities.json",
            params={"iss.meta": "off"},
        )

    def get_security(self, secid: str) -> Dict[str, Any]:
        return self._get_json(f"/iss/securities/{secid}.json", params={"iss.meta": "off"})

    def get_fx_spot(self, currency: str) -> Dict[str, Any]:
        params = {
            "iss.meta": "off",
            "iss.only": "marketdata",
        }
        return self._get_json(f"/iss/engines/currency/markets/selt/boards/CETS/securities/{currency}RUB.json", params=params)
