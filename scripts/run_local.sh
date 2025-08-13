#!/usr/bin/env bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "Para iniciar la API:"
echo "uvicorn src.api:app --reload --port 8000"
