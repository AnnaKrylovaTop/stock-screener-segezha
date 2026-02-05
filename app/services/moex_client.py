from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://iss.moex.com/iss"


@dataclass(frozen=True)
class CacheEntry:
    path: Path
    expires_at: datetime


def _cache_key(url: str, params: dict | None) -> str:
    payload = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_cache(cache_dir: Path, key: str) -> dict | None:
    meta_path = cache_dir / f"{key}.meta.json"
    data_path = cache_dir / f"{key}.json"
    if not meta_path.exists() or not data_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        expires_at = datetime.fromisoformat(meta["expires_at"])
        if datetime.utcnow() > expires_at:
            return None
        return json.loads(data_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        logger.warning("Не удалось прочитать кэш: %s", exc)
        return None


def _write_cache(cache_dir: Path, key: str, payload: dict, ttl: timedelta) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / f"{key}.meta.json"
    data_path = cache_dir / f"{key}.json"
    expires_at = datetime.utcnow() + ttl
    meta = {"expires_at": expires_at.isoformat()}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _request_json(url: str, params: dict | None, timeout: int, retries: int) -> dict:
    last_exc: Exception | None = None
    for _ in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            logger.warning("Ошибка запроса MOEX: %s", exc)
    raise RuntimeError("Не удалось получить данные MOEX") from last_exc


class MoexClient:
    def __init__(self, cache_dir: Path, timeout: int = 10, retries: int = 2) -> None:
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.retries = retries

    def _get(self, endpoint: str, params: dict | None, ttl: timedelta) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        key = _cache_key(url, params)
        cached = _read_cache(self.cache_dir, key)
        if cached is not None:
            return cached
        payload = _request_json(url, params=params, timeout=self.timeout, retries=self.retries)
        _write_cache(self.cache_dir, key, payload, ttl)
        return payload

    def futures_list(self) -> Dict[str, Any]:
        payload = self._get(
            "engines/futures/markets/forts/securities.json",
            params={"iss.meta": "off"},
            ttl=timedelta(hours=24),
        )
        return payload.get("securities", {})

    def futures_marketdata(self) -> Dict[str, Any]:
        payload = self._get(
            "engines/futures/markets/forts/marketdata.json",
            params={"iss.meta": "off"},
            ttl=timedelta(minutes=10),
        )
        return payload.get("marketdata", {})

    def futures_contracts(self) -> Dict[str, Any]:
        payload = self._get(
            "engines/futures/markets/forts/securities.json",
            params={"iss.meta": "off", "iss.only": "securities"},
            ttl=timedelta(hours=24),
        )
        return payload.get("securities", {})
