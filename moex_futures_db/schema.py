from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from moex_futures_db.constants import SCHEMA_VERSION
from moex_futures_db.serializer import canonical_dumps, write_if_changed


@dataclass(frozen=True)
class SchemaBundle:
    schema: dict[str, Any]
    provenance: dict[str, Any]


def build_schema() -> SchemaBundle:
    schema = {
        "schema_version": SCHEMA_VERSION,
        "description": "LLM-friendly MOEX FORTS futures reference schema",
        "sections": {
            "identity": "Identifiers and basic names from MOEX",
            "exchange": "Raw and normalized fields from MOEX ISS",
            "derived": "Computed or normalized fields",
            "llm_view": "Compact card for LLM consumption",
            "provenance": "Source endpoints and hashes",
        },
        "top_level_order": [
            "identity",
            "exchange",
            "derived",
            "llm_view",
            "provenance",
        ],
        "normalized_fields": {
            "contract_type": "Contract type (if available in ISS)",
            "underlying": "Underlying asset description",
            "currency": "Trading currency",
            "lot_size": "Lot size",
            "min_step": "Minimum price step",
            "step_price": "Price step value",
            "settlement_type": "Settlement type",
            "delivery_type": "Delivery type",
            "expiry": "Expiration date (if available)",
        },
    }
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "rules": {
            "exchange_info": "Any field coming from MOEX ISS response",
            "derived": "Computed or normalized values",
        },
        "field_groups": {
            "exchange": {"exchange_info": True, "derived": False},
            "derived": {"exchange_info": False, "derived": True},
        },
    }
    return SchemaBundle(schema=schema, provenance=provenance)


def write_schema(out_dir: str) -> dict[str, bool]:
    bundle = build_schema()
    schema_path = _schema_path(out_dir, "schema.json")
    provenance_path = _schema_path(out_dir, "field_provenance.json")
    schema_written = write_if_changed(schema_path, canonical_dumps(bundle.schema))
    provenance_written = write_if_changed(
        provenance_path, canonical_dumps(bundle.provenance)
    )
    return {
        "schema": schema_written,
        "field_provenance": provenance_written,
    }


def _schema_path(out_dir: str, name: str):
    from pathlib import Path

    return Path(out_dir) / "schema" / name
