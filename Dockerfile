FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    APP_FILE=app_unloadv1.7.py

LABEL org.opencontainers.image.title="readyworkday"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Patch streamlit_extras: replace deprecated components.v1.html calls with st.iframe
# (streamlit removes components.v1.html after 2026-06-01)
RUN python - <<'EOF'
import re
from pathlib import Path

extras_dir = Path("/usr/local/lib").glob("python*/site-packages/streamlit_extras")
for base in extras_dir:
    for f in base.rglob("__init__.py"):
        text = f.read_text(encoding="utf-8")
        original = text
        text = re.sub(r"\bcomponents\.html\(", "st.iframe(", text)
        text = re.sub(r"^from streamlit\.components\.v1 import html\n", "", text, flags=re.MULTILINE)
        text = re.sub(r"(?<!\.)(?<!\w)\bhtml\(", "st.iframe(", text)
        text = re.sub(r",\s*scrolling\s*=\s*(True|False)", "", text)
        text = re.sub(r"\bscrolling\s*=\s*(True|False)\s*,\s*", "", text)
        if text != original:
            f.write_text(text, encoding="utf-8")
EOF

COPY . .

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
