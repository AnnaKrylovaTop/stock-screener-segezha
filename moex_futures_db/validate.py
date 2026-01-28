from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from moex_futures_db.constants import SCHEMA_VERSION
from moex_futures_db.serializer import canonical_dumps, canonical_hash

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


def validate_db(db_dir: str) -> None:
    db_path = Path(db_dir)
    schema_path = db_path / "schema" / "schema.json"
    if not schema_path.exists():
        raise ValidationError("schema.json missing")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    expected_order = schema.get("top_level_order", [])

    instruments_path = db_path / "instruments"
    if not instruments_path.exists():
        raise ValidationError("instruments directory missing")

    errors: list[str] = []
    for path in instruments_path.glob("*.json"):
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue

        if list(data.keys()) != expected_order:
            errors.append(f"{path.name}: top-level key order mismatch")

        canonical = canonical_dumps(data)
        if canonical != content:
            errors.append(f"{path.name}: not canonical JSON formatting")

        if data.get("provenance", {}).get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{path.name}: schema_version mismatch")

        hash_expected = data.get("provenance", {}).get("content_hash")
        if hash_expected:
            hash_payload = {
                "identity": _raw_identity_payload(data),
                "exchange_raw": data.get("exchange", {}).get("raw", {}),
            }
            if canonical_hash(hash_payload) != hash_expected:
                errors.append(f"{path.name}: content_hash mismatch")

    if errors:
        raise ValidationError("; ".join(errors))
    logger.info("Validation successful", extra={"count": len(list(instruments_path.glob('*.json')))} )


def _raw_identity_payload(document: dict[str, Any]) -> dict[str, Any]:
    exchange_raw = document.get("exchange", {}).get("raw", {})
    return {
        "SECID": exchange_raw.get("SECID"),
        "BOARDID": exchange_raw.get("BOARDID"),
        "ENGINE": exchange_raw.get("ENGINE"),
        "MARKET": exchange_raw.get("MARKET"),
        "SHORTNAME": exchange_raw.get("SHORTNAME"),
        "NAME": exchange_raw.get("NAME"),
        "LATNAME": exchange_raw.get("LATNAME"),
    }
