from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import ceil

from data import FuturesInstrument


@dataclass(frozen=True)
class HedgeRequest:
    industry: str
    currency: str
    volume: float
    buy_date: date
    sell_date: date


@dataclass(frozen=True)
class HedgeResult:
    instrument: FuturesInstrument
    contracts_needed: int
    notional_value: float
    estimated_cost: float
    coverage: float


def calculate_hedge(request: HedgeRequest, instrument: FuturesInstrument) -> HedgeResult:
    contracts_needed = max(1, ceil(request.volume / instrument.contract_size))
    notional_value = contracts_needed * instrument.contract_size
    estimated_cost = contracts_needed * instrument.contract_size * instrument.price
    coverage = min(1.0, request.volume / notional_value)

    return HedgeResult(
        instrument=instrument,
        contracts_needed=contracts_needed,
        notional_value=notional_value,
        estimated_cost=estimated_cost,
        coverage=coverage,
    )


def select_instruments(
    instruments: list[FuturesInstrument],
    request: HedgeRequest,
    max_results: int = 3,
) -> list[HedgeResult]:
    candidates = [
        instrument
        for instrument in instruments
        if instrument.industry == request.industry and instrument.currency == request.currency
    ]

    if not candidates:
        candidates = [
            instrument
            for instrument in instruments
            if instrument.currency == request.currency
        ]

    windowed = [
        instrument
        for instrument in candidates
        if request.buy_date <= instrument.expiry <= request.sell_date
    ]

    if windowed:
        candidates = windowed

    def distance_to_window(instrument: FuturesInstrument) -> int:
        if instrument.expiry < request.buy_date:
            return (request.buy_date - instrument.expiry).days
        if instrument.expiry > request.sell_date:
            return (instrument.expiry - request.sell_date).days
        return 0

    candidates.sort(key=lambda instrument: (distance_to_window(instrument), instrument.expiry))

    return [calculate_hedge(request, instrument) for instrument in candidates[:max_results]]
