#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python -m streamlit run app/mentivio_app.py --server.headless true --server.port 8501

