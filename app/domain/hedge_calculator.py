from __future__ import annotations

import math
from typing import Iterable, List

from .models import ExposureInput, FutureContract, HedgeOption


def _commission_total(notional_rub: float, contracts_count: int, per_contract: float, percent: float) -> float:
    return contracts_count * per_contract + notional_rub * percent


def build_hedge_options(
    exposure: ExposureInput,
    contracts: Iterable[FutureContract],
    commission_config: dict,
) -> List[HedgeOption]:
    options: List[HedgeOption] = []
    per_contract = float(commission_config["commission"]["per_contract_rub"])
    percent = float(commission_config["commission"]["percent_notional"])

    for contract in contracts:
        contract_size = max(contract.contract_size, 1.0)
        contracts_count = int(math.ceil(exposure.amount / contract_size))
        notional_currency = contract_size * contracts_count
        notional_rub = notional_currency * contract.price
        margin_total = None
        if contract.initial_margin is not None:
            margin_total = contract.initial_margin * contracts_count
        commission_total = _commission_total(notional_rub, contracts_count, per_contract, percent)
        note = "Ближе к вашей дате" if contract.expiration_date >= exposure.target_date else "Чуть раньше вашей даты"
        options.append(
            HedgeOption(
                contract=contract,
                contracts_count=contracts_count,
                notional_currency=notional_currency,
                notional_rub=notional_rub,
                margin_total=margin_total,
                commission_total=commission_total,
                rate_hint=contract.price,
                note=note,
            )
        )

    return options
