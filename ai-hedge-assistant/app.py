from __future__ import annotations

import logging
from datetime import date, timedelta

import streamlit as st

from src.config_loader import load_yaml
from src.hedge_calculator import build_hedge_options
from src.instruments import filter_by_currency, parse_futures_securities
from src.logging_setup import setup_logging
from src.moex_client import MoexClient
from src.scenarios import build_scenarios
from src.ui_components import (
    render_comparison_table,
    render_option_card,
    render_scenarios_chart,
    render_scenarios_table,
)

setup_logging()
LOGGER = logging.getLogger(__name__)

st.set_page_config(page_title="AI Hedge Assistant", layout="wide")

with open("assets/theme.css", "r", encoding="utf-8") as handle:
    st.markdown(f"<style>{handle.read()}</style>", unsafe_allow_html=True)

st.image("assets/logo_placeholder.svg", width=300)

st.title("AI Финансовый ассистент для хеджирования валютных рисков")

industries_config = load_yaml("config/industries.yml")
industries = industries_config.get("industries", [])

left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("Параметры")
    industry_names = [item["name"] for item in industries]
    industry_choice = st.selectbox("Отрасль", industry_names)
    industry_info = next(item for item in industries if item["name"] == industry_choice)
    default_currency = industry_info.get("default_currency", "USD")

    profile = st.radio("Профиль операции", ["Импорт", "Экспорт"], horizontal=True)
    currency = st.selectbox("Валюта риска", ["USD", "EUR", "CNY"], index=["USD", "EUR", "CNY"].index(default_currency))
    volume = st.number_input("Объём валюты", min_value=0.0, value=25000.0, step=1000.0)
    date_input = st.date_input(
        "Дата хеджируемой покупки/продажи",
        value=date.today() + timedelta(days=60),
    )
    hedge_ratio = st.slider("Доля хеджа, %", min_value=0, max_value=100, value=100)
    commission = st.number_input("Комиссия за 1 контракт (RUB)", min_value=0.0, value=0.0, step=1.0)

    st.caption(f"Подсказка: {industry_info.get('notes', '')}")

    if isinstance(date_input, tuple) or isinstance(date_input, list):
        start, end = date_input
        center_date = start + (end - start) / 2
        st.info(
            f"Вы указали диапазон дат. В MVP используем центр диапазона: {center_date}."
        )
        hedge_date = center_date
    else:
        hedge_date = date_input

    scenario_change = st.slider(
        "Сценарное изменение курса к дате, %",
        min_value=-30,
        max_value=30,
        value=10,
    )

    submit = st.button("Подобрать")

with right_col:
    st.subheader("Результаты")
    if submit:
        client = MoexClient()
        with st.spinner("Запрашиваем данные MOEX..."):
            try:
                futures_payload = client.get_futures_list()
                contracts = parse_futures_securities(futures_payload)
                currency_contracts = filter_by_currency(contracts, currency)
            except RuntimeError as exc:
                st.error(f"Ошибка при запросе MOEX ISS: {exc}")
                st.stop()

        if not currency_contracts:
            st.warning("Не найдено фьючерсов по выбранной валюте.")
            st.stop()

        options = build_hedge_options(
            currency_contracts,
            target_amount=volume,
            hedge_ratio=hedge_ratio,
            commission_per_contract=commission,
            profile=profile,
            hedge_date=hedge_date,
        )

        if not options:
            st.warning("Не удалось рассчитать варианты: проверьте параметры.")
            st.stop()

        st.write(
            "Для импорта: покупать валютные фьючерсы для защиты от роста курса. "
            "Для экспорта: продавать фьючерсы для защиты от падения курса. "
            "Это образовательная информация, а не торговая рекомендация."
        )

        for option in options:
            render_option_card(option)

        st.subheader("Сравнение вариантов")
        render_comparison_table(options)

        selected = options[0]
        st.subheader("Сценарный анализ")
        futures_price = selected.hedge_rate or 0
        if futures_price == 0:
            st.warning("Нет цены фьючерса. Сценарный анализ ограничен.")
        else:
            try:
                spot_payload = client.get_fx_spot(currency)
                marketdata = spot_payload.get("marketdata", {})
                columns = marketdata.get("columns", [])
                data = marketdata.get("data", [])
                current_spot = None
                if data:
                    row = dict(zip(columns, data[0]))
                    current_spot = row.get("LAST") or row.get("LCURRENTPRICE")
            except RuntimeError as exc:
                LOGGER.warning("Spot request failed: %s", exc)
                current_spot = None

            if current_spot is None:
                current_spot = futures_price
                st.caption("Спот используется как прокси из цены ближайшего фьючерса.")

            pct_points = [
                -scenario_change,
                -scenario_change / 2,
                0,
                scenario_change / 2,
                scenario_change,
            ]
            results = build_scenarios(
                direction=selected.direction,
                target_amount=selected.target_amount,
                hedged_amount=selected.hedged_amount,
                futures_price=futures_price,
                current_spot=current_spot,
                pct_range=pct_points,
            )
            render_scenarios_table(results)
            render_scenarios_chart(results)

st.caption("ГО/initial margin — обеспечение, не расход. Комиссия — прямой расход.")
