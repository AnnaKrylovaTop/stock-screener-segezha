from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List

from .models import FutureContract


@dataclass(frozen=True)
class SelectionResult:
    contracts: List[FutureContract]
    notes: List[str]


def _distance_days(expiration: date, target: date) -> int:
    return abs((expiration - target).days)


def select_contracts(
    contracts: Iterable[FutureContract],
    target_date: date,
    second_date: date | None = None,
    limit: int = 3,
) -> SelectionResult:
    available = list(contracts)
    if not available:
        return SelectionResult([], ["Не найдено контрактов по выбранной валюте."])

    notes: List[str] = []
    if second_date:
        start = min(target_date, second_date)
        end = max(target_date, second_date)
        in_range = [c for c in available if start <= c.expiration_date <= end]
        if in_range:
            sorted_contracts = sorted(in_range, key=lambda c: _distance_days(c.expiration_date, target_date))
            notes.append("Контракты подобраны по диапазону дат.")
        else:
            sorted_contracts = sorted(available, key=lambda c: _distance_days(c.expiration_date, start))
            notes.append(
                "Точных контрактов в диапазоне нет — показаны ближайшие к границам даты.")
    else:
        sorted_contracts = sorted(available, key=lambda c: _distance_days(c.expiration_date, target_date))

    selected = sorted_contracts[:limit]
    if len(selected) < limit:
        notes.append("Доступно меньше контрактов, чем запрошено.")

    return SelectionResult(selected, notes)
