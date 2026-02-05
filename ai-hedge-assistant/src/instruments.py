from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .config_loader import load_yaml


@dataclass
class FutureContract:
    secid: str
    name: str
    currency: str
    expiry: Optional[datetime]
    last_price: Optional[float]
    settle_price: Optional[float]
    contract_size: Optional[float]
    price_step: Optional[float]
    quote_currency: Optional[str]
    initial_margin: Optional[float]

    @property
    def effective_price(self) -> Optional[float]:
        return self.last_price or self.settle_price


def _table_to_dicts(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    columns = table.get("columns", [])
    data = table.get("data", [])
    return [dict(zip(columns, row)) for row in data]


def parse_futures_securities(payload: Dict[str, Any]) -> List[FutureContract]:
    securities = _table_to_dicts(payload.get("securities", {}))
    marketdata = _table_to_dicts(payload.get("marketdata", {}))
    marketdata_map = {row.get("SECID"): row for row in marketdata}
    fallback = load_yaml("config/currency_futures_fallback.yml").get("fallback_contract_size", {})

    contracts: List[FutureContract] = []
    for sec in securities:
        secid = sec.get("SECID")
        if not secid:
            continue
        mdata = marketdata_map.get(secid, {})
        expiry_raw = sec.get("MATDATE") or sec.get("LASTTRADEDATE")
        expiry = None
        if expiry_raw:
            expiry = datetime.strptime(expiry_raw, "%Y-%m-%d")

        # Определение валюты по префиксу SECID
            secid_prefix = secid[:2] if len(secid) >= 2 else ""
            currency_map = {"Si": "USD", "Eu": "EUR", "CR": "CNY"}
            currency = currency_map.get(secid_prefix, sec.get("FACEUNIT", ""))
        contract_size = sec.get("LOTVALUE") or sec.get("LOT") or sec.get("LOTSIZE")
        if contract_size is None and currency in fallback:
            contract_size = fallback[currency]

        initial_margin = (
            mdata.get("INITIALMARGIN")
            or mdata.get("MARGINBUY")
            or mdata.get("MARGINSELL")
            or sec.get("INITIALMARGIN")
            or sec.get("MARGINBUY")
            or sec.get("MARGINSELL")
        )

        contracts.append(
            FutureContract(
                secid=secid,
                name=sec.get("SHORTNAME") or sec.get("SECNAME") or secid,
                currency=currency,
                expiry=expiry,
                last_price=mdata.get("LAST") or sec.get("LAST") or None,
                settle_price=mdata.get("SETTLEPRICE") or sec.get("SETTLEPRICE") or None,
                contract_size=contract_size,
                price_step=sec.get("MINSTEP"),
                quote_currency=sec.get("FACEUNIT") or sec.get("CURRENCYID"),
                initial_margin=initial_margin,
            )
        )

    return contracts


def parse_security_details(payload: Dict[str, Any]) -> Dict[str, Any]:
    securities = _table_to_dicts(payload.get("securities", {}))
    marketdata = _table_to_dicts(payload.get("marketdata", {}))
    sec = securities[0] if securities else {}
    mdata = marketdata[0] if marketdata else {}

    return {
        "contract_size": sec.get("LOTVALUE") or sec.get("LOT") or sec.get("LOTSIZE"),
        "price_step": sec.get("MINSTEP"),
        "initial_margin": mdata.get("INITIALMARGIN")
        or mdata.get("MARGINBUY")
        or mdata.get("MARGINSELL"),
    }


def filter_by_currency(contracts: Iterable[FutureContract], currency: str) -> List[FutureContract]:
    return [contract for contract in contracts if contract.currency.upper() == currency.upper()]
