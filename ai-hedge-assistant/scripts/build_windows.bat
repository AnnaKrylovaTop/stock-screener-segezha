@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
pip install -U pip
pip install -e .
pip install pyinstaller

pytest -q

pyinstaller --noconfirm --clean --onefile --name AIHedgeAssistant --add-data "assets;assets" --add-data "config;config" launcher.py
