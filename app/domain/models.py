from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class ExposureInput:
    industry: str
    currency: str
    direction: str
    amount: float
    target_date: date
    second_date: Optional[date] = None


@dataclass(frozen=True)
class FutureContract:
    secid: str
    shortname: str
    name: str
    expiration_date: date
    currency: str
    contract_size: float
    price: float
    initial_margin: Optional[float] = None


@dataclass(frozen=True)
class HedgeOption:
    contract: FutureContract
    contracts_count: int
    notional_currency: float
    notional_rub: float
    margin_total: Optional[float]
    commission_total: float
    rate_hint: float
    note: str


@dataclass(frozen=True)
class ScenarioResult:
    label: str
    without_hedge_rub: float
    with_hedge_rub: float
