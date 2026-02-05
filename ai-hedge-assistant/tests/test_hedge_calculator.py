import json
from datetime import date
from pathlib import Path

from src.hedge_calculator import build_hedge_options, calculate_contracts, determine_direction
from src.instruments import parse_futures_securities


def load_fixture(name: str):
    path = Path(__file__).parent / "fixtures" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_determine_direction():
    assert determine_direction("Импорт") == "LONG"
    assert determine_direction("Экспорт") == "SHORT"


def test_calculate_contracts_rounding():
    assert calculate_contracts(25000, 1000) == 25
    assert calculate_contracts(25500, 1000) == 26


def test_build_hedge_options_integration():
    payload = load_fixture("moex_futures_sample.json")
    contracts = parse_futures_securities(payload)
    options = build_hedge_options(
        contracts,
        target_amount=25000,
        hedge_ratio=100,
        commission_per_contract=5,
        profile="Импорт",
        hedge_date=date(2025, 1, 10),
    )
    assert len(options) >= 3
    first = options[0]
    assert first.contracts_needed > 0
    assert first.hedged_amount > 0
    assert first.commission_total == first.contracts_needed * 5
