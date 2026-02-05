from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Optional

from .instruments import FutureContract


@dataclass
class HedgeOption:
    contract: FutureContract
    direction: str
    target_amount: float
    hedge_ratio: float
    contracts_needed: int
    hedged_amount: float
    coverage_pct: float
    hedge_rate: Optional[float]
    commission_total: float
    initial_margin_total: Optional[float]


def determine_direction(profile: str) -> str:
    profile_lower = profile.strip().lower()
    if profile_lower == "импорт":
        return "LONG"
    if profile_lower == "экспорт":
        return "SHORT"
    raise ValueError("Профиль операции должен быть Импорт или Экспорт")


def select_contracts(
    contracts: Iterable[FutureContract],
    hedge_date: date,
    max_count: int = 5,
) -> List[FutureContract]:
    sorted_contracts = sorted(
        contracts,
        key=lambda item: item.expiry or datetime.max,
    )
    future_contracts = [c for c in sorted_contracts if c.expiry and c.expiry.date() >= hedge_date]
    if future_contracts:
        return future_contracts[:max_count]
    return sorted_contracts[:max_count]


def calculate_contracts(
    target_amount: float,
    contract_size: float,
) -> int:
    if contract_size <= 0:
        raise ValueError("Размер контракта должен быть больше 0")
    return int(round(target_amount / contract_size))


def build_hedge_options(
    contracts: Iterable[FutureContract],
    target_amount: float,
    hedge_ratio: float,
    commission_per_contract: float,
    profile: str,
    hedge_date: date,
) -> List[HedgeOption]:
    direction = determine_direction(profile)
    effective_target = target_amount * (hedge_ratio / 100)
    chosen = select_contracts(contracts, hedge_date, max_count=5)
    options: List[HedgeOption] = []

    for contract in chosen:
        contract_size = contract.contract_size or 0
        if contract_size <= 0:
            continue
        contracts_needed = calculate_contracts(effective_target, contract_size)
        hedged_amount = contracts_needed * contract_size
        coverage_pct = (hedged_amount / effective_target) * 100 if effective_target else 0
        commission_total = contracts_needed * commission_per_contract
        initial_margin_total = (
            contracts_needed * contract.initial_margin
            if contract.initial_margin is not None
            else None
        )

        options.append(
            HedgeOption(
                contract=contract,
                direction=direction,
                target_amount=effective_target,
                hedge_ratio=hedge_ratio,
                contracts_needed=contracts_needed,
                hedged_amount=hedged_amount,
                coverage_pct=coverage_pct,
                hedge_rate=contract.effective_price,
                commission_total=commission_total,
                initial_margin_total=initial_margin_total,
            )
        )

    return options
