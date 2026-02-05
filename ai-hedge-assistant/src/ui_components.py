from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from .hedge_calculator import HedgeOption
from .scenarios import ScenarioResult


def render_option_card(option: HedgeOption) -> None:
    contract = option.contract
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            f"<span class='badge'>{contract.secid}</span> {contract.name}",
            unsafe_allow_html=True,
        )
        st.write(f"Экспирация: {contract.expiry.date() if contract.expiry else 'нет данных'}")
        st.write(f"Направление: {option.direction}")
        st.write(f"Цена фьючерса: {option.hedge_rate or 'нет данных'}")
        st.write(f"Размер контракта: {contract.contract_size}")
        st.write(f"Контрактов: {option.contracts_needed}")
        st.write(f"Перекрыто: {option.hedged_amount} ({option.coverage_pct:.1f}%)")
        st.write(f"Комиссия: {option.commission_total:,.2f} RUB")
        if option.initial_margin_total is None:
            st.write("ГО/initial margin: нет данных из ISS")
        else:
            st.write(f"ГО/initial margin: {option.initial_margin_total:,.2f} RUB")
        st.markdown("</div>", unsafe_allow_html=True)


def render_comparison_table(options: List[HedgeOption]) -> None:
    data = [
        {
            "SECID": option.contract.secid,
            "Экспирация": option.contract.expiry.date() if option.contract.expiry else "нет",
            "Цена": option.hedge_rate,
            "Размер": option.contract.contract_size,
            "Контрактов": option.contracts_needed,
            "Покрытие %": round(option.coverage_pct, 1),
            "Комиссия": round(option.commission_total, 2),
        }
        for option in options
    ]
    st.dataframe(pd.DataFrame(data))


def render_scenarios_table(results: List[ScenarioResult]) -> None:
    table = pd.DataFrame(
        [
            {
                "Изменение %": res.pct_change,
                "Спот": round(res.spot_rate, 2),
                "Спот (руб)": round(res.spot_value, 2),
                "PnL фьючерсов": round(res.futures_pnl, 2),
                "Итог": round(res.net_effect, 2),
            }
            for res in results
        ]
    )
    st.dataframe(table, use_container_width=True)


def render_scenarios_chart(results: List[ScenarioResult]) -> None:
    chart_df = pd.DataFrame(
        {
            "Изменение %": [res.pct_change for res in results],
            "Итог": [res.net_effect for res in results],
        }
    )
    st.line_chart(chart_df, x="Изменение %", y="Итог")
