@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
pip install -U pip
pip install -e .

streamlit run app.py
