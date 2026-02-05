from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from data import CURRENCIES, INDUSTRIES, INSTRUMENTS
from hedging import HedgeRequest, select_instruments


class HedgeAssistantApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI Финансовый ассистент по валютному хеджированию")
        self.geometry("980x720")
        self.configure(bg="#0f172a")

        self._build_header()
        self._build_overview()
        self._build_form()
        self._build_results()
        self._build_summary()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#0f172a")
        header.pack(fill="x", padx=32, pady=(24, 12))

        title = tk.Label(
            header,
            text="AI Финансовый ассистент",
            font=("Segoe UI", 22, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text=(
                "Подбор инструментов Московской биржи для защиты валютной выручки "
                "и импортных платежей"
            ),
            font=("Segoe UI", 11),
            fg="#94a3b8",
            bg="#0f172a",
        )
        subtitle.pack(anchor="w", pady=(8, 0))

    def _build_overview(self) -> None:
        overview = tk.Frame(self, bg="#0f172a")
        overview.pack(fill="x", padx=32)

        card = tk.Frame(overview, bg="#111827", highlightbackground="#1e293b", highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        text = (
            "Постройте сценарий хеджирования валютных рисков под импорт или экспорт. "
            "Ассистент подберет ближайшие по срокам инструменты Мосбиржи и рассчитает "
            "стоимость защиты для заданного объема валюты."
        )
        label = tk.Label(
            card,
            text=text,
            wraplength=880,
            justify="left",
            font=("Segoe UI", 10),
            fg="#cbd5f5",
            bg="#111827",
            padx=18,
            pady=12,
        )
        label.pack(anchor="w")

    def _build_form(self) -> None:
        form_frame = tk.Frame(self, bg="#0f172a")
        form_frame.pack(fill="x", padx=32)

        card = tk.Frame(form_frame, bg="#111827", highlightbackground="#1e293b", highlightthickness=1)
        card.pack(fill="x", pady=(12, 18))

        hint = tk.Label(
            card,
            text="Заполните ключевые параметры сделки и нажмите «Подобрать».",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#111827",
        )
        hint.grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(16, 0))

        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(2, weight=1)
        card.grid_columnconfigure(3, weight=1)

        self.industry_var = tk.StringVar(value=INDUSTRIES[0])
        self.currency_var = tk.StringVar(value=CURRENCIES[0])
        self.volume_var = tk.StringVar(value="50000")
        self.buy_date_var = tk.StringVar(value=date.today().isoformat())
        self.sell_date_var = tk.StringVar(value=date.today().replace(month=12, day=19).isoformat())

        self._add_field(card, "Отрасль бизнеса", self._build_dropdown(card, self.industry_var, INDUSTRIES), 0)
        self._add_field(
            card, "Валюта хеджирования", self._build_dropdown(card, self.currency_var, CURRENCIES), 1
        )
        self._add_field(card, "Объем валюты", self._build_entry(card, self.volume_var), 2)
        self._add_field(card, "Дата покупки", self._build_entry(card, self.buy_date_var), 3)
        self._add_field(card, "Дата продажи", self._build_entry(card, self.sell_date_var), 4)

        button = tk.Button(
            card,
            text="Подобрать",
            command=self._on_submit,
            bg="#38bdf8",
            fg="#0f172a",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=24,
            pady=8,
            activebackground="#7dd3fc",
            activeforeground="#0f172a",
        )
        button.grid(row=3, column=3, sticky="e", padx=20, pady=(0, 18))

    def _build_results(self) -> None:
        results_frame = tk.Frame(self, bg="#0f172a")
        results_frame.pack(fill="both", expand=True, padx=32, pady=(0, 24))

        label = tk.Label(
            results_frame,
            text="Рекомендованные инструменты",
            font=("Segoe UI", 12, "bold"),
            fg="#e2e8f0",
            bg="#0f172a",
        )
        label.pack(anchor="w", pady=(0, 10))

        columns = ("code", "name", "expiry", "contracts", "coverage", "cost")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=8)
        self.tree.pack(fill="both", expand=True)

        headings = {
            "code": "Код",
            "name": "Инструмент",
            "expiry": "Экспирация",
            "contracts": "Контракты",
            "coverage": "Покрытие",
            "cost": "Оценка затрат (₽)",
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, anchor="center")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#0b1220",
            fieldbackground="#0b1220",
            foreground="#e2e8f0",
            rowheight=36,
            bordercolor="#1e293b",
            borderwidth=1,
        )
        style.configure(
            "Treeview.Heading",
            background="#111827",
            foreground="#f8fafc",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#1e293b")])

    def _build_summary(self) -> None:
        summary = tk.Frame(self, bg="#0f172a")
        summary.pack(fill="x", padx=32, pady=(0, 24))

        self.summary_count = tk.StringVar(value="0")
        self.summary_cost = tk.StringVar(value="—")
        self.summary_coverage = tk.StringVar(value="—")

        self._summary_card(summary, "Подобрано инструментов", self.summary_count).pack(
            side="left", expand=True, fill="x", padx=(0, 12)
        )
        self._summary_card(summary, "Оценка затрат", self.summary_cost).pack(
            side="left", expand=True, fill="x", padx=(0, 12)
        )
        self._summary_card(summary, "Среднее покрытие", self.summary_coverage).pack(
            side="left", expand=True, fill="x"
        )

    def _summary_card(self, parent: tk.Widget, title: str, value: tk.StringVar) -> tk.Frame:
        card = tk.Frame(parent, bg="#111827", highlightbackground="#1e293b", highlightthickness=1)
        label = tk.Label(card, text=title, font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
        label.pack(anchor="w", padx=16, pady=(12, 0))
        metric = tk.Label(
            card,
            textvariable=value,
            font=("Segoe UI", 13, "bold"),
            fg="#f8fafc",
            bg="#111827",
        )
        metric.pack(anchor="w", padx=16, pady=(4, 12))
        return card

    def _build_dropdown(self, parent: tk.Widget, variable: tk.StringVar, values: list[str]) -> ttk.Combobox:
        dropdown = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        dropdown.configure(font=("Segoe UI", 10))
        return dropdown

    def _build_entry(self, parent: tk.Widget, variable: tk.StringVar) -> ttk.Entry:
        entry = ttk.Entry(parent, textvariable=variable, font=("Segoe UI", 10))
        return entry

    def _add_field(self, parent: tk.Widget, label: str, widget: tk.Widget, column: int) -> None:
        field = tk.Frame(parent, bg="#111827")
        row = 2 if column > 2 else 1
        field.grid(row=row, column=column % 4, sticky="ew", padx=20, pady=(18, 8))

        title = tk.Label(field, text=label, font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827")
        title.pack(anchor="w")
        widget.pack(fill="x", pady=(6, 0))

    def _on_submit(self) -> None:
        try:
            volume = float(self.volume_var.get().replace(" ", "").replace(",", "."))
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректный объем валюты.")
            return

        if volume <= 0:
            messagebox.showerror("Ошибка", "Объем валюты должен быть больше нуля.")
            return

        try:
            buy_date = date.fromisoformat(self.buy_date_var.get())
            sell_date = date.fromisoformat(self.sell_date_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Укажите даты в формате ГГГГ-ММ-ДД.")
            return

        if buy_date > sell_date:
            messagebox.showerror("Ошибка", "Дата покупки должна быть раньше даты продажи.")
            return

        request = HedgeRequest(
            industry=self.industry_var.get(),
            currency=self.currency_var.get(),
            volume=volume,
            buy_date=buy_date,
            sell_date=sell_date,
        )
        results = select_instruments(INSTRUMENTS, request)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for result in results:
            self.tree.insert(
                "",
                "end",
                values=(
                    result.instrument.code,
                    result.instrument.name,
                    result.instrument.expiry.isoformat(),
                    result.contracts_needed,
                    f"{result.coverage:.0%}",
                    f"{result.estimated_cost:,.0f}",
                ),
            )

        if results:
            costs = [result.estimated_cost for result in results]
            coverages = [result.coverage for result in results]
            self.summary_count.set(str(len(results)))
            self.summary_cost.set(f"{min(costs):,.0f} – {max(costs):,.0f} ₽")
            self.summary_coverage.set(f"{sum(coverages) / len(coverages):.0%}")
        else:
            self.summary_count.set("0")
            self.summary_cost.set("—")
            self.summary_coverage.set("—")


if __name__ == "__main__":
    app = HedgeAssistantApp()
    app.mainloop()
