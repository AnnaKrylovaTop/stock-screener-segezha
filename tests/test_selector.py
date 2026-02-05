from datetime import date, timedelta

from app.domain.instrument_selector import select_contracts
from app.domain.models import FutureContract


def _contract(days: int, secid: str) -> FutureContract:
    return FutureContract(
        secid=secid,
        shortname=secid,
        name=secid,
        expiration_date=date.today() + timedelta(days=days),
        currency="USD",
        contract_size=1000,
        price=95.0,
    )


def test_select_contracts_nearest_three() -> None:
    contracts = [_contract(30, "A"), _contract(60, "B"), _contract(90, "C"), _contract(120, "D")]
    target = date.today() + timedelta(days=70)
    result = select_contracts(contracts, target)
    assert [c.secid for c in result.contracts] == ["B", "C", "A"]
    assert result.notes == []


def test_select_contracts_range() -> None:
    contracts = [_contract(30, "A"), _contract(60, "B"), _contract(120, "C")]
    target = date.today() + timedelta(days=40)
    second = date.today() + timedelta(days=110)
    result = select_contracts(contracts, target, second_date=second)
    assert [c.secid for c in result.contracts] == ["B"]
    assert "диапазону" in result.notes[0]
