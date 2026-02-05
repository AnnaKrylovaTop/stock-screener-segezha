import json
from pathlib import Path

from src.instruments import filter_by_currency, parse_futures_securities, parse_security_details


def load_fixture(name: str):
    path = Path(__file__).parent / "fixtures" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_parse_futures_securities():
    payload = load_fixture("moex_futures_sample.json")
    contracts = parse_futures_securities(payload)
    assert len(contracts) == 3
    usd_contracts = filter_by_currency(contracts, "USD")
    assert len(usd_contracts) == 2
    assert usd_contracts[0].contract_size == 1000
    assert usd_contracts[0].effective_price == 92.5


def test_parse_security_details():
    payload = load_fixture("moex_security_sample.json")
    details = parse_security_details(payload)
    assert details["contract_size"] == 1000
    assert details["price_step"] == 0.0025
    assert details["initial_margin"] == 6500
