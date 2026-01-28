# MOEX FORTS Futures Reference DB

Production-quality Python project that builds and maintains a local, LLM-friendly reference database of **all MOEX FORTS futures** from MOEX ISS API.

## Features
- Fetches columns dynamically from `/columns` (no hard-coded column list).
- Separates exchange-provided data from derived data.
- One instrument per file for minimal diffs.
- Incremental updates (byte-for-byte stability when unchanged).
- JSON schema and provenance metadata.
- CLI and pytest-based self-test.

## CLI
```bash
python -m moex_futures_db sync --out ./db
python -m moex_futures_db validate --db ./db
python -m moex_futures_db selftest
python -m moex_futures_db selftest --live
```

## Storage layout
```
db/
  schema/
    schema.json
    field_provenance.json
  instruments/
    <SECID>.json
  index/
    instruments_index.jsonl
  runs/
    <YYYYMMDD_HHMMSS>.json
```

### Index strategy
`index/instruments_index.jsonl` stores **one line per SECID**, sorted by SECID. The file is re-written only if its content changes; this keeps diffs minimal. New instruments or status changes update only the corresponding line content.

## Instrument document
Top-level key order is fixed and validated:
1. `identity`
2. `exchange`
3. `derived`
4. `llm_view`
5. `provenance`

Exchange data is stored in two forms:
- `exchange.raw`: full row from ISS
- `exchange.normalized`: human-friendly subset (only when fields are available)

Derived data is stored under `derived`.

## Self-test
`selftest` runs offline tests by default. `--live` performs a minimal live request to ISS to ensure parsing works against real data.

## Example instrument (mocked)
```json
{
  "identity": {
    "secid": "SRH5",
    "board": "RFUD",
    "engine": "futures",
    "market": "forts",
    "shortname": "Sample Fut",
    "name": "Sample Futures",
    "latname": "Sample Futures"
  },
  "exchange": {
    "raw": {
      "SECID": "SRH5",
      "BOARDID": "RFUD",
      "ENGINE": "futures",
      "MARKET": "forts",
      "SHORTNAME": "Sample Fut",
      "NAME": "Sample Futures",
      "LATNAME": "Sample Futures",
      "UNDERLYINGASSET": "Test Asset",
      "CURRENCYID": "RUB"
    },
    "normalized": {
      "underlying": "Test Asset",
      "currency": "RUB"
    }
  },
  "derived": {
    "normalized_text": {
      "name": "Sample Futures",
      "shortname": "Sample Fut",
      "latname": "Sample Futures",
      "description": null
    },
    "instrument_summary": "Фьючерс Sample Futures. Базовый актив: Test Asset.",
    "tokens": [
      "asset",
      "актив",
      "базовый",
      "futures",
      "sample",
      "test",
      "фьючерс"
    ]
  },
  "llm_view": {
    "secid": "SRH5",
    "name": "Sample Futures",
    "market": "forts",
    "underlying": "Test Asset",
    "currency": "RUB",
    "expiry": null,
    "summary": "Фьючерс Sample Futures. Базовый актив: Test Asset."
  },
  "provenance": {
    "source_endpoints": [
      "engines/futures/markets/forts/securities",
      "engines/futures/markets/forts/securities/columns"
    ],
    "schema_version": "1.0.0",
    "content_hash": "<sha256>"
  }
}
```

## Development
- Python 3.11+
- `ruff` for linting (`ruff check .`)
- `pytest` for testing (`pytest`)

### HTTP client note
The runtime uses `httpx` if it is installed. If not, it falls back to a small built-in HTTP client compatible with the minimal API used here (useful in restricted environments).
