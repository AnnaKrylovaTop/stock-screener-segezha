from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ScenarioResult:
    pct_change: float
    spot_rate: float
    spot_value: float
    futures_pnl: float
    net_effect: float


def build_scenarios(
    direction: str,
    target_amount: float,
    hedged_amount: float,
    futures_price: float,
    current_spot: float,
    pct_range: List[float],
) -> List[ScenarioResult]:
    results: List[ScenarioResult] = []
    for pct in pct_range:
        spot_rate = current_spot * (1 + pct / 100)
        spot_value = target_amount * spot_rate
        if direction == "LONG":
            futures_pnl = (spot_rate - futures_price) * hedged_amount
            net_effect = spot_value - futures_pnl
        else:
            futures_pnl = (futures_price - spot_rate) * hedged_amount
            net_effect = spot_value + futures_pnl
        results.append(
            ScenarioResult(
                pct_change=pct,
                spot_rate=spot_rate,
                spot_value=spot_value,
                futures_pnl=futures_pnl,
                net_effect=net_effect,
            )
        )
    return results
