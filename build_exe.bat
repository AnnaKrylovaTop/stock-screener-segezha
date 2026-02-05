@echo off
setlocal

call .venv\Scripts\activate
pyinstaller --onefile --noconsole --name ai_fx_hedge app\main.py
