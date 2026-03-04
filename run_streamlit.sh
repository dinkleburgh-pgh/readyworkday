#!/bin/bash
# Activate venv and run Streamlit app in background for code-server/TrueNAS
cd "$(dirname "$0")"
if [ -d venv ]; then
  source venv/bin/activate
else
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
fi
nohup streamlit run app_unloadv1.2.py --server.port 8501 --server.headless true > .data/streamlit.log 2>&1 &
