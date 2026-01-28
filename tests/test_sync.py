import time
from pathlib import Path

from moex_futures_db.sync import sync_db
from moex_futures_db.validate import validate_db


class FakeClient:
    def __init__(self, columns, rows):
        self._columns = columns
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def fetch_columns(self):
        return self._columns

    def fetch_securities(self):
        return list(self._rows)


def _sample_rows():
    return [
        {
            "SECID": "SRH5",
            "BOARDID": "RFUD",
            "ENGINE": "futures",
            "MARKET": "forts",
            "SHORTNAME": "Sample Fut",
            "NAME": "Sample Futures",
            "LATNAME": "Sample Futures",
            "UNDERLYINGASSET": "Test Asset",
            "CURRENCYID": "RUB",
        },
        {
            "SECID": "SRM5",
            "BOARDID": "RFUD",
            "ENGINE": "futures",
            "MARKET": "forts",
            "SHORTNAME": "Second Fut",
            "NAME": "Second Futures",
            "LATNAME": "Second Futures",
            "UNDERLYINGASSET": "Second Asset",
            "CURRENCYID": "RUB",
        },
    ]


def test_sync_incremental(tmp_path: Path):
    columns = [{"name": "SECID"}]
    rows = _sample_rows()
    client = FakeClient(columns, rows)

    sync_db(str(tmp_path), client)
    instrument_path = tmp_path / "instruments" / "SRH5.json"
    original_mtime = instrument_path.stat().st_mtime

    time.sleep(1)
    sync_db(str(tmp_path), client)
    assert instrument_path.stat().st_mtime == original_mtime


def test_sync_change_only_one(tmp_path: Path):
    columns = [{"name": "SECID"}]
    rows = _sample_rows()
    client = FakeClient(columns, rows)
    sync_db(str(tmp_path), client)

    first_path = tmp_path / "instruments" / "SRH5.json"
    second_path = tmp_path / "instruments" / "SRM5.json"
    first_content = first_path.read_text(encoding="utf-8")
    second_content = second_path.read_text(encoding="utf-8")

    time.sleep(1)
    rows_changed = _sample_rows()
    rows_changed[0] = {**rows_changed[0], "CURRENCYID": "USD"}
    sync_db(str(tmp_path), FakeClient(columns, rows_changed))

    assert first_path.read_text(encoding="utf-8") != first_content
    assert second_path.read_text(encoding="utf-8") == second_content


def test_validate(tmp_path: Path):
    columns = [{"name": "SECID"}]
    rows = _sample_rows()
    sync_db(str(tmp_path), FakeClient(columns, rows))
    validate_db(str(tmp_path))
