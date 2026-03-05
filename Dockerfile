FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    APP_FILE=app_unloadv1.3.py

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "APP_PATH=\"${APP_FILE}\"; if [ ! -f \"$APP_PATH\" ]; then APP_PATH=$(ls app_unloadv*.py 2>/dev/null | sort -V | tail -n 1); fi; if [ -z \"$APP_PATH\" ]; then echo 'No app_unloadv*.py file found.' >&2; exit 1; fi; streamlit run \"$APP_PATH\" --server.port=${STREAMLIT_SERVER_PORT} --server.address=${STREAMLIT_SERVER_ADDRESS} --server.headless=true"]
