# AI Финансовый ассистент для хеджирования валютных рисков

MVP-приложение помогает малому/среднему бизнесу оценить варианты хеджирования валютного риска с помощью валютных фьючерсов MOEX. Приложение **не торгует** и не размещает заявки — только рассчитывает и визуализирует сценарии.

## Возможности
- Подбор 3–5 вариантов фьючерсных контрактов по экспирациям вокруг даты хеджа.
- Расчёт количества контрактов, покрываемого объёма и условно фиксируемого курса.
- Оценка стоимости хеджа (комиссии и ГО/initial margin — если доступно в ISS).
- Сценарный анализ влияния изменения курса.
- Красно-белый строгий корпоративный UI на Streamlit.

## Быстрый старт (локально)

### 1) Установка
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -U pip
pip install -e .
```

### 2) Запуск в dev
```bash
streamlit run app.py
```

### 3) Тесты
```bash
pytest -q
```

## Сборка .exe (Windows)
Скрипт `scripts/build_windows.bat`:
1. создаёт venv (если нет)
2. ставит зависимости
3. запускает pytest
4. собирает exe

Запуск:
```bat
scripts\build_windows.bat
```

После завершения сборки ожидается файл:
```
dist\AIHedgeAssistant.exe
```

## Как работает подбор
1. Выберите отрасль (из `config/industries.yml`). Это влияет на подсказки и валюту по умолчанию.
2. Укажите профиль операции (Импорт/Экспорт), валюту риска, объём, дату и долю хеджа.
3. Нажмите “Подобрать” — приложение найдёт подходящие фьючерсы и рассчитает варианты.

### Источник данных
Используется публичный MOEX ISS API:
- `/iss/engines/futures/markets/forts/boards/rfud/securities.json`
- `/iss/securities/{SECID}.json`

Данные кешируются на 45 секунд, чтобы не перегружать сеть.

## Типичные проблемы и решения
- **Нет данных по ГО/initial margin** — MOEX ISS не всегда отдаёт поля `INITIALMARGIN/MARGINBUY/MARGINSELL`. Приложение покажет “нет данных из ISS” и всё равно продолжит расчёт.
- **Сетевая ошибка** — проверьте интернет и повторите. Внутри есть ретраи с таймаутом.
- **Не запускается Streamlit** — проверьте, что зависимости установлены и активирован venv.

## Структура проекта
```
ai-hedge-assistant/
  app.py
  launcher.py
  src/
    __init__.py
    moex_client.py
    instruments.py
    hedge_calculator.py
    scenarios.py
    ui_components.py
    config_loader.py
    logging_setup.py
  config/
    industries.yml
    currency_futures_fallback.yml
  assets/
    theme.css
    logo_placeholder.svg
  tests/
    test_moex_client_parsing.py
    test_hedge_calculator.py
    test_scenarios.py
    fixtures/
      moex_futures_sample.json
      moex_security_sample.json
      moex_fx_spot_sample.json
  scripts/
    run_dev.bat
    build_windows.bat
  pyproject.toml
  README.md
```
