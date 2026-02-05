from __future__ import annotations

from typing import List

from .models import ExposureInput, HedgeOption, ScenarioResult


SCENARIOS = [
    ("+10%", 1.10),
    ("0%", 1.00),
    ("-10%", 0.90),
]


def build_scenarios(
    exposure: ExposureInput,
    option: HedgeOption,
    spot_reference: float,
) -> List[ScenarioResult]:
    results: List[ScenarioResult] = []
    for label, factor in SCENARIOS:
        spot_t = spot_reference * factor
        without_hedge = exposure.amount * spot_t
        futures_pnl = (spot_t - option.rate_hint) * option.contract.contract_size * option.contracts_count
        if exposure.direction == "Импорт: купить валюту":
            with_hedge = without_hedge - futures_pnl
        else:
            with_hedge = without_hedge + futures_pnl
        results.append(
            ScenarioResult(
                label=label,
                without_hedge_rub=without_hedge,
                with_hedge_rub=with_hedge,
            )
        )
    return results
