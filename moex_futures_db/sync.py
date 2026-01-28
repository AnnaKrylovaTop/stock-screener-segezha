from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from moex_futures_db.constants import COLUMNS_ENDPOINT, SCHEMA_VERSION, SECURITIES_ENDPOINT
from moex_futures_db.iss_client import ISSClient
from moex_futures_db.schema import write_schema
from moex_futures_db.serializer import (
    canonical_dumps,
    canonical_hash,
    compact_dumps,
    write_if_changed,
)

logger = logging.getLogger(__name__)


NORMALIZED_FIELD_MAP = {
    "TYPE": "contract_type",
    "UNDERLYINGASSET": "underlying",
    "ASSETCODE": "underlying_code",
    "CURRENCYID": "currency",
    "LOTSIZE": "lot_size",
    "MINSTEP": "min_step",
    "STEPPRICE": "step_price",
    "SETTLETIME": "settlement_type",
    "DELIVERYTYPE": "delivery_type",
    "LASTTRADINGDATE": "expiry",
}

IDENTITY_FIELDS = [
    "SECID",
    "BOARDID",
    "ENGINE",
    "MARKET",
    "SHORTNAME",
    "NAME",
    "LATNAME",
]


class SyncStats:
    def __init__(self) -> None:
        self.total = 0
        self.written = 0
        self.unchanged = 0
        self.archived = 0
        self.new = 0
        self.schema_written = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "written": self.written,
            "unchanged": self.unchanged,
            "archived": self.archived,
            "new": self.new,
            "schema_written": self.schema_written,
        }


def sync_db(out_dir: str, client: ISSClient) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    stats = SyncStats()
    stats.schema_written = write_schema(out_dir)

    columns = client.fetch_columns()
    securities = list(client.fetch_securities())
    stats.total = len(securities)

    existing_index = _load_index(out_path)
    current_secids = set()

    for row in securities:
        secid = row.get("SECID")
        if not secid:
            continue
        current_secids.add(secid)
        document, content_hash = build_instrument_document(row)
        doc_path = out_path / "instruments" / f"{secid}.json"
        existing_hash = _read_existing_hash(doc_path)
        if existing_hash == content_hash:
            stats.unchanged += 1
        else:
            write_if_changed(doc_path, canonical_dumps(document))
            stats.written += 1
            if existing_hash is None:
                stats.new += 1

        entry = _build_index_entry(
            secid=secid,
            path=str(doc_path.relative_to(out_path)),
            status="active",
            content_hash=content_hash,
            archived_at=None,
            previous=existing_index.get(secid),
        )
        existing_index[secid] = entry

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for secid, entry in list(existing_index.items()):
        if secid not in current_secids and entry.get("status") != "inactive":
            archived = _build_index_entry(
                secid=secid,
                path=entry["path"],
                status="inactive",
                content_hash=entry["content_hash"],
                archived_at=timestamp,
                previous=entry,
            )
            existing_index[secid] = archived
            stats.archived += 1

    _write_index(out_path, existing_index)
    _write_run_metadata(out_path, timestamp, stats, columns)
    logger.info("Sync completed", extra={"stats": stats.to_dict()})


def build_instrument_document(row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    identity = _build_identity(row)
    exchange_raw = dict(row)
    exchange_normalized = _normalize_exchange(row)
    derived = _build_derived(row, exchange_normalized)
    llm_view = _build_llm_view(identity, exchange_normalized, derived)

    hash_payload = {
        "identity": _raw_identity_payload(row),
        "exchange_raw": exchange_raw,
    }
    content_hash = canonical_hash(hash_payload)

    document = {
        "identity": identity,
        "exchange": {
            "raw": exchange_raw,
            "normalized": exchange_normalized,
        },
        "derived": derived,
        "llm_view": llm_view,
        "provenance": {
            "source_endpoints": [SECURITIES_ENDPOINT, COLUMNS_ENDPOINT],
            "schema_version": SCHEMA_VERSION,
            "content_hash": content_hash,
        },
    }
    return document, content_hash


def _build_identity(row: dict[str, Any]) -> dict[str, Any]:
    identity = {
        "secid": row.get("SECID"),
        "board": row.get("BOARDID"),
        "engine": row.get("ENGINE"),
        "market": row.get("MARKET"),
        "shortname": _clean_text(row.get("SHORTNAME")),
        "name": _clean_text(row.get("NAME")),
        "latname": _clean_text(row.get("LATNAME")),
    }
    return identity


def _raw_identity_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "SECID": row.get("SECID"),
        "BOARDID": row.get("BOARDID"),
        "ENGINE": row.get("ENGINE"),
        "MARKET": row.get("MARKET"),
        "SHORTNAME": row.get("SHORTNAME"),
        "NAME": row.get("NAME"),
        "LATNAME": row.get("LATNAME"),
    }


def _normalize_exchange(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for iss_key, target in NORMALIZED_FIELD_MAP.items():
        if iss_key in row:
            normalized[target] = row.get(iss_key)
    return normalized


def _build_derived(row: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    name_parts = [
        _clean_text(row.get("NAME")),
        _clean_text(row.get("SHORTNAME")),
        _clean_text(row.get("LATNAME")),
    ]
    description = _clean_text(row.get("DESCRIPTION"))
    summary = _build_summary(name_parts, normalized, description)
    tokens = _build_tokens(summary)
    return {
        "normalized_text": {
            "name": name_parts[0],
            "shortname": name_parts[1],
            "latname": name_parts[2],
            "description": description,
        },
        "instrument_summary": summary,
        "tokens": tokens,
    }


def _build_llm_view(
    identity: dict[str, Any],
    normalized: dict[str, Any],
    derived: dict[str, Any],
) -> dict[str, Any]:
    return {
        "secid": identity.get("secid"),
        "name": identity.get("name") or identity.get("shortname"),
        "market": identity.get("market"),
        "underlying": normalized.get("underlying"),
        "currency": normalized.get("currency"),
        "expiry": normalized.get("expiry"),
        "summary": derived.get("instrument_summary"),
    }


def _build_summary(
    name_parts: list[str | None],
    normalized: dict[str, Any],
    description: str | None,
) -> str:
    base_name = next((part for part in name_parts if part), "")
    pieces = []
    if base_name:
        pieces.append(f"Фьючерс {base_name}.")
    underlying = normalized.get("underlying")
    if underlying:
        pieces.append(f"Базовый актив: {underlying}.")
    contract_type = normalized.get("contract_type")
    if contract_type:
        pieces.append(f"Тип контракта: {contract_type}.")
    expiry = normalized.get("expiry")
    if expiry:
        pieces.append(f"Дата экспирации: {expiry}.")
    if description:
        pieces.append(description)
    if not pieces:
        return "Фьючерсный контракт MOEX FORTS."
    text = " ".join(pieces)
    return _clean_text(text) or "Фьючерсный контракт MOEX FORTS."


def _build_tokens(summary: str) -> list[str]:
    import re

    cleaned = re.sub(r"[^\w]+", " ", summary.lower(), flags=re.UNICODE)
    tokens = cleaned.split()
    return sorted({token for token in tokens if token})


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    text = " ".join(text.split())
    return text or None


def _read_existing_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = __import__("json").loads(content)
    except ValueError:
        return None
    return data.get("provenance", {}).get("content_hash")


def _load_index(out_path: Path) -> dict[str, dict[str, Any]]:
    index_path = out_path / "index" / "instruments_index.jsonl"
    if not index_path.exists():
        return {}
    entries = {}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = __import__("json").loads(line)
        entries[item["secid"]] = item
    return entries


def _build_index_entry(
    secid: str,
    path: str,
    status: str,
    content_hash: str,
    archived_at: str | None,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    entry = {
        "secid": secid,
        "status": status,
        "path": path,
        "content_hash": content_hash,
        "archived_at": archived_at,
    }
    if previous:
        for key in ["first_seen"]:
            if key in previous:
                entry[key] = previous[key]
    if "first_seen" not in entry:
        entry["first_seen"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return entry


def _write_index(out_path: Path, entries: dict[str, dict[str, Any]]) -> None:
    index_path = out_path / "index" / "instruments_index.jsonl"
    lines = [compact_dumps(entry) for entry in _sorted_entries(entries)]
    content = "\n".join(lines) + "\n"
    write_if_changed(index_path, content)


def _sorted_entries(entries: dict[str, dict[str, Any]]):
    for secid in sorted(entries):
        yield entries[secid]


def _write_run_metadata(
    out_path: Path, timestamp: str, stats: SyncStats, columns: Iterable[dict[str, Any]]
) -> None:
    run_path = out_path / "runs" / f"{timestamp}.json"
    payload = {
        "timestamp": timestamp,
        "stats": stats.to_dict(),
        "endpoints": [SECURITIES_ENDPOINT, COLUMNS_ENDPOINT],
        "columns": list(columns),
    }
    write_if_changed(run_path, canonical_dumps(payload))
