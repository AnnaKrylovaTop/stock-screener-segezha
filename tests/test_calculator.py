from datetime import date

from app.domain.hedge_calculator import build_hedge_options
from app.domain.models import ExposureInput, FutureContract
from app.domain.scenarios import build_scenarios


def test_build_hedge_options_counts_and_commissions() -> None:
    exposure = ExposureInput(
        industry="Импортёр оборудования",
        currency="USD",
        direction="Импорт: купить валюту",
        amount=2500,
        target_date=date.today(),
    )
    contract = FutureContract(
        secid="USD-3.24",
        shortname="USD",
        name="USD",
        expiration_date=date.today(),
        currency="USD",
        contract_size=1000,
        price=90.0,
        initial_margin=5000.0,
    )
    commission = {"commission": {"per_contract_rub": 10.0, "percent_notional": 0.001}}
    options = build_hedge_options(exposure, [contract], commission)

    assert options[0].contracts_count == 3
    assert options[0].notional_currency == 3000
    assert options[0].notional_rub == 270000
    assert options[0].margin_total == 15000
    assert options[0].commission_total == 10.0 * 3 + 270000 * 0.001


def test_build_scenarios_direction() -> None:
    exposure = ExposureInput(
        industry="Экспортёр",
        currency="USD",
        direction="Экспорт: продать валюту",
        amount=1000,
        target_date=date.today(),
    )
    contract = FutureContract(
        secid="USD-3.24",
        shortname="USD",
        name="USD",
        expiration_date=date.today(),
        currency="USD",
        contract_size=1000,
        price=90.0,
        initial_margin=5000.0,
    )
    commission = {"commission": {"per_contract_rub": 10.0, "percent_notional": 0.001}}
    option = build_hedge_options(exposure, [contract], commission)[0]
    scenarios = build_scenarios(exposure, option, spot_reference=90.0)

    base = scenarios[1]
    assert base.label == "0%"
    assert base.without_hedge_rub == 90000
    assert base.with_hedge_rub == 90000
