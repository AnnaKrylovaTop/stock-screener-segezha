from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FuturesInstrument:
    code: str
    name: str
    industry: str
    currency: str
    contract_size: float
    price: float
    expiry: date


INSTRUMENTS: list[FuturesInstrument] = [
    FuturesInstrument(
        code="Si-12.24",
        name="Фьючерс USD/RUB",
        industry="Экспорт сырья",
        currency="USD",
        contract_size=1000.0,
        price=97.50,
        expiry=date(2024, 12, 19),
    ),
    FuturesInstrument(
        code="Si-03.25",
        name="Фьючерс USD/RUB",
        industry="Импорт потребительских товаров",
        currency="USD",
        contract_size=1000.0,
        price=98.20,
        expiry=date(2025, 3, 20),
    ),
    FuturesInstrument(
        code="Eu-12.24",
        name="Фьючерс EUR/RUB",
        industry="Импорт оборудования",
        currency="EUR",
        contract_size=1000.0,
        price=105.40,
        expiry=date(2024, 12, 19),
    ),
    FuturesInstrument(
        code="Eu-03.25",
        name="Фьючерс EUR/RUB",
        industry="Экспорт продукции АПК",
        currency="EUR",
        contract_size=1000.0,
        price=106.10,
        expiry=date(2025, 3, 20),
    ),
    FuturesInstrument(
        code="CNY-12.24",
        name="Фьючерс CNY/RUB",
        industry="Импорт электроники",
        currency="CNY",
        contract_size=10000.0,
        price=13.50,
        expiry=date(2024, 12, 19),
    ),
    FuturesInstrument(
        code="CNY-03.25",
        name="Фьючерс CNY/RUB",
        industry="Логистика и транспорт",
        currency="CNY",
        contract_size=10000.0,
        price=13.85,
        expiry=date(2025, 3, 20),
    ),
]


INDUSTRIES: list[str] = sorted({instrument.industry for instrument in INSTRUMENTS})
CURRENCIES: list[str] = sorted({instrument.currency for instrument in INSTRUMENTS})
