FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    APP_FILE=app_unloadv1.6.py \
    APP_VERSION=1.6.5

LABEL org.opencontainers.image.title="readyworkday" \
      org.opencontainers.image.version="1.6.5" \
      org.opencontainers.image.created="2026-03-16"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
