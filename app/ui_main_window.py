from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from PySide6 import QtCharts, QtCore, QtGui, QtWidgets

from app.domain.hedge_calculator import build_hedge_options
from app.domain.instrument_selector import select_contracts
from app.domain.models import ExposureInput, FutureContract
from app.domain.scenarios import build_scenarios
from app.services.moex_client import MoexClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigBundle:
    industries: List[dict]
    commissions: dict
    fallback_specs: dict


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config_dir: Path, cache_dir: Path) -> None:
        super().__init__()
        self.setWindowTitle("AI Финансовый ассистент — хеджирование валютных рисков")
        self.resize(1280, 720)
        self.setMinimumSize(1200, 680)

        self.config = self._load_configs(config_dir)
        self.cache_dir = cache_dir
        self.moex_client = MoexClient(cache_dir=cache_dir)
        self.last_update_label = QtWidgets.QLabel("Данные: не обновлялись")

        self._build_ui()
        self._apply_theme()

    def _load_configs(self, config_dir: Path) -> ConfigBundle:
        industries = yaml.safe_load((config_dir / "industries.yml").read_text(encoding="utf-8"))
        commissions = yaml.safe_load((config_dir / "commissions.yml").read_text(encoding="utf-8"))
        fallback_specs = yaml.safe_load((config_dir / "fallback_contract_specs.yml").read_text(encoding="utf-8"))
        return ConfigBundle(
            industries=industries["industries"],
            commissions=commissions,
            fallback_specs=fallback_specs["fallback_specs"],
        )

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("AI Финансовый ассистент для хеджирования валютных рисков")
        title.setObjectName("headerTitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.last_update_label)
        root_layout.addLayout(header)

        body_layout = QtWidgets.QHBoxLayout()
        root_layout.addLayout(body_layout)

        form_widget = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(form_widget)

        self.industry_combo = QtWidgets.QComboBox()
        for item in self.config.industries:
            self.industry_combo.addItem(item["name"], userData=item)
        form_layout.addWidget(QtWidgets.QLabel("Отрасль / профиль бизнеса"))
        form_layout.addWidget(self.industry_combo)

        self.currency_combo = QtWidgets.QComboBox()
        self.currency_combo.addItems(["USD", "EUR", "CNY"])
        form_layout.addWidget(QtWidgets.QLabel("Валюта экспозиции"))
        form_layout.addWidget(self.currency_combo)

        self.direction_combo = QtWidgets.QComboBox()
        self.direction_combo.addItems(["Импорт: купить валюту", "Экспорт: продать валюту"])
        form_layout.addWidget(QtWidgets.QLabel("Направление"))
        form_layout.addWidget(self.direction_combo)

        self.amount_input = QtWidgets.QDoubleSpinBox()
        self.amount_input.setMaximum(1_000_000_000)
        self.amount_input.setValue(100000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)
        form_layout.addWidget(QtWidgets.QLabel("Объём валюты"))
        form_layout.addWidget(self.amount_input)

        self.date_picker = QtWidgets.QDateEdit()
        self.date_picker.setDate(QtCore.QDate.currentDate().addMonths(2))
        self.date_picker.setCalendarPopup(True)
        form_layout.addWidget(QtWidgets.QLabel("Дата операции"))
        form_layout.addWidget(self.date_picker)

        self.second_date_checkbox = QtWidgets.QCheckBox("Есть вторая дата")
        self.second_date_picker = QtWidgets.QDateEdit()
        self.second_date_picker.setCalendarPopup(True)
        self.second_date_picker.setEnabled(False)
        self.second_date_checkbox.stateChanged.connect(self._toggle_second_date)
        form_layout.addWidget(self.second_date_checkbox)
        form_layout.addWidget(self.second_date_picker)

        self.pick_button = QtWidgets.QPushButton("Подобрать")
        self.reset_button = QtWidgets.QPushButton("Сброс")
        self.pick_button.clicked.connect(self._on_pick)
        self.reset_button.clicked.connect(self._on_reset)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.pick_button)
        button_layout.addWidget(self.reset_button)
        form_layout.addLayout(button_layout)
        form_layout.addStretch()

        body_layout.addWidget(form_widget, 1)

        results_widget = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_widget)

        self.kpi_layout = QtWidgets.QHBoxLayout()
        self.kpi_cards = {
            "contract": self._create_kpi_card("Рекомендуемый контракт", "—"),
            "contracts": self._create_kpi_card("Контрактов нужно", "—"),
            "margin": self._create_kpi_card("ГО", "—"),
            "rate": self._create_kpi_card("Ориентир фиксируемого курса", "—"),
        }
        for card in self.kpi_cards.values():
            self.kpi_layout.addWidget(card)
        results_layout.addLayout(self.kpi_layout)

        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "SECID",
                "Экспирация",
                "Размер контракта",
                "Цена",
                "Контрактов",
                "ГО",
                "Комиссии",
                "Примечание",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        results_layout.addWidget(self.table, 2)

        self.explanation = QtWidgets.QTextEdit()
        self.explanation.setReadOnly(True)
        self.explanation.setPlaceholderText("Пояснения по расчётам появятся здесь")
        results_layout.addWidget(self.explanation, 1)

        self.chart = QtCharts.QChart()
        self.chart.legend().setVisible(True)
        self.chart_view = QtCharts.QChartView(self.chart)
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
        results_layout.addWidget(self.chart_view, 2)

        body_layout.addWidget(results_widget, 2)

        self.setCentralWidget(central)

        self.industry_combo.currentIndexChanged.connect(self._sync_currency)
        self._sync_currency()

    def _create_kpi_card(self, title: str, value: str) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setObjectName("kpiCard")
        layout = QtWidgets.QVBoxLayout(frame)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("kpiTitle")
        value_label = QtWidgets.QLabel(value)
        value_label.setObjectName("kpiValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        frame.value_label = value_label
        return frame

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background-color: #111418; color: #E6E8EB; font-size: 14px; }
            QFrame#kpiCard { background-color: #1B1F24; border-radius: 8px; padding: 12px; }
            QLabel#headerTitle { font-size: 20px; font-weight: 600; }
            QLabel#kpiTitle { color: #9AA4AE; }
            QLabel#kpiValue { font-size: 18px; font-weight: 600; }
            QPushButton { background-color: #2D6CDF; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background-color: #3A7CF2; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QTextEdit { background-color: #1B1F24; border: 1px solid #2A2F36; border-radius: 6px; padding: 4px; }
            QTableWidget { background-color: #1B1F24; border: 1px solid #2A2F36; }
            QHeaderView::section { background-color: #1B1F24; border: none; color: #9AA4AE; }
            QCheckBox { padding: 4px; }
            """
        )

    def _toggle_second_date(self) -> None:
        self.second_date_picker.setEnabled(self.second_date_checkbox.isChecked())

    def _sync_currency(self) -> None:
        item = self.industry_combo.currentData()
        if not item:
            return
        default_currency = item.get("default_currency")
        idx = self.currency_combo.findText(default_currency)
        if idx >= 0:
            self.currency_combo.setCurrentIndex(idx)

    def _on_reset(self) -> None:
        self.amount_input.setValue(100000)
        self.direction_combo.setCurrentIndex(0)
        self.date_picker.setDate(QtCore.QDate.currentDate().addMonths(2))
        self.second_date_checkbox.setChecked(False)
        self.table.setRowCount(0)
        self.explanation.clear()
        self._update_kpis("—", "—", "—", "—")
        self._update_chart([], [])

    def _on_pick(self) -> None:
        try:
            exposure = self._build_exposure()
            contracts = self._load_contracts(exposure.currency)
            selection = select_contracts(contracts, exposure.target_date, exposure.second_date)
            options = build_hedge_options(exposure, selection.contracts, self.config.commissions)
            self._render_results(exposure, options, selection.notes)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            logger.exception("Ошибка подбора")
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось обновить данные MOEX: {exc}. Попробуйте ещё раз.",
            )

    def _build_exposure(self) -> ExposureInput:
        second_date = None
        if self.second_date_checkbox.isChecked():
            second_date = self.second_date_picker.date().toPython()
        return ExposureInput(
            industry=self.industry_combo.currentText(),
            currency=self.currency_combo.currentText(),
            direction=self.direction_combo.currentText(),
            amount=float(self.amount_input.value()),
            target_date=self.date_picker.date().toPython(),
            second_date=second_date,
        )

    def _load_contracts(self, currency: str) -> List[FutureContract]:
        securities = self.moex_client.futures_contracts()
        marketdata = self.moex_client.futures_marketdata()
        sec_rows = _to_dicts(securities.get("columns", []), securities.get("data", []))
        md_rows = _to_dicts(marketdata.get("columns", []), marketdata.get("data", []))
        md_map = {row.get("SECID"): row for row in md_rows}

        contracts: List[FutureContract] = []
        for row in sec_rows:
            secid = row.get("SECID")
            if not secid:
                continue
            detected_currency = _detect_currency(secid, row.get("SHORTNAME"), row.get("NAME"))
            if detected_currency != currency:
                continue
            expiration = _parse_expiration(row)
            if not expiration:
                continue
            contract_size = float(row.get("LOTSIZE") or row.get("LOTVALUE") or 0)
            if contract_size <= 0:
                contract_size = float(self.config.fallback_specs[currency]["contract_size"])
            md = md_map.get(secid, {})
            price = _pick_price(md)
            initial_margin = md.get("INITIALMARGIN") or md.get("IMINITIALMARGIN")
            initial_margin_value = float(initial_margin) if initial_margin else None
            contracts.append(
                FutureContract(
                    secid=secid,
                    shortname=row.get("SHORTNAME") or secid,
                    name=row.get("NAME") or secid,
                    expiration_date=expiration,
                    currency=currency,
                    contract_size=contract_size,
                    price=price,
                    initial_margin=initial_margin_value,
                )
            )
        if contracts:
            self.last_update_label.setText(f"Данные обновлены: {datetime.now():%H:%M:%S}")
        return contracts

    def _render_results(self, exposure: ExposureInput, options: List, notes: List[str]) -> None:
        if not options:
            self.table.setRowCount(0)
            self.explanation.setPlainText("Не найдено подходящих контрактов. Проверьте параметры.")
            return

        best = options[0]
        margin_text = f"{best.margin_total:,.0f} ₽" if best.margin_total else "—"
        self._update_kpis(
            best.contract.secid,
            str(best.contracts_count),
            margin_text,
            f"{best.rate_hint:,.4f} ₽",
        )

        self.table.setRowCount(len(options))
        for idx, option in enumerate(options):
            self.table.setItem(idx, 0, QtWidgets.QTableWidgetItem(option.contract.secid))
            self.table.setItem(idx, 1, QtWidgets.QTableWidgetItem(option.contract.expiration_date.isoformat()))
            self.table.setItem(idx, 2, QtWidgets.QTableWidgetItem(f"{option.contract.contract_size:,.0f}"))
            self.table.setItem(idx, 3, QtWidgets.QTableWidgetItem(f"{option.contract.price:,.4f}"))
            self.table.setItem(idx, 4, QtWidgets.QTableWidgetItem(str(option.contracts_count)))
            margin = f"{option.margin_total:,.0f} ₽" if option.margin_total else "—"
            self.table.setItem(idx, 5, QtWidgets.QTableWidgetItem(margin))
            self.table.setItem(idx, 6, QtWidgets.QTableWidgetItem(f"{option.commission_total:,.0f} ₽"))
            self.table.setItem(idx, 7, QtWidgets.QTableWidgetItem(option.note))

        explanation_lines = [
            "Подбор использует валютные фьючерсы MOEX с ближайшей экспирацией к вашей дате.",
            "Для импортёра хедж — длинная позиция, для экспортёра — короткая.",
            "Комиссии и ГО рассчитаны упрощённо, значения можно настроить.",
            "Сценарии используют приближение: PnL_fut ≈ (F_t - F_0) * размер контракта * кол-во.",
        ] + notes
        self.explanation.setPlainText("\n".join(explanation_lines))

        scenarios = build_scenarios(exposure, best, best.contract.price)
        without = [s.without_hedge_rub for s in scenarios]
        with_hedge = [s.with_hedge_rub for s in scenarios]
        labels = [s.label for s in scenarios]
        self._update_chart(labels, [without, with_hedge])

    def _update_kpis(self, contract: str, contracts: str, margin: str, rate: str) -> None:
        self.kpi_cards["contract"].value_label.setText(contract)
        self.kpi_cards["contracts"].value_label.setText(contracts)
        self.kpi_cards["margin"].value_label.setText(margin)
        self.kpi_cards["rate"].value_label.setText(rate)

    def _update_chart(self, labels: List[str], series_values: List[List[float]]) -> None:
        self.chart.removeAllSeries()
        if not labels:
            return
        axis_x = QtCharts.QBarCategoryAxis()
        axis_x.append(labels)
        axis_y = QtCharts.QValueAxis()
        axis_y.setLabelFormat("%'.0f")

        set_without = QtCharts.QBarSet("Без хеджа")
        set_with = QtCharts.QBarSet("С хеджем")
        set_without.append(series_values[0])
        set_with.append(series_values[1])

        series = QtCharts.QBarSeries()
        series.append(set_without)
        series.append(set_with)
        self.chart.addSeries(series)
        self.chart.setAxisX(axis_x, series)
        self.chart.setAxisY(axis_y, series)
        self.chart.setTitle("Сценарный анализ")


def _to_dicts(columns: List[str], data: List[List]) -> List[Dict[str, Optional[str]]]:
    rows: List[Dict[str, Optional[str]]] = []
    for row in data:
        rows.append({columns[idx]: row[idx] for idx in range(len(columns))})
    return rows


def _detect_currency(secid: str, shortname: Optional[str], name: Optional[str]) -> Optional[str]:
    blob = " ".join([secid or "", shortname or "", name or ""]).upper()
    if "USD" in blob:
        return "USD"
    if "EUR" in blob:
        return "EUR"
    if "CNY" in blob or "CNH" in blob:
        return "CNY"
    return None


def _parse_expiration(row: Dict[str, Optional[str]]) -> Optional[date]:
    for key in ["EXPIRATIONDATE", "MATDATE", "LASTDELDATE", "LASTTRADEDATE"]:
        value = row.get(key)
        if value:
            try:
                return datetime.fromisoformat(str(value)).date()
            except ValueError:
                continue
    return None


def _pick_price(marketdata: Dict[str, Optional[str]]) -> float:
    for key in ["LAST", "MARKETPRICE", "SETTLEPRICE", "PREVSETTLEPRICE"]:
        value = marketdata.get(key)
        if value not in (None, ""):
            return float(value)
    return 0.0
