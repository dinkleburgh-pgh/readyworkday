#!/bin/sh

set -eu

APP_PATH=""

: "${APP_FILE:=app_unloadv1.7.py}"
if [ -f "${APP_FILE}" ]; then
  APP_PATH="${APP_FILE}"
fi

if [ -z "$APP_PATH" ]; then
  for candidate in app_unloadv*.py app_unload*.py; do
    if [ -f "$candidate" ]; then
      APP_PATH="$candidate"
    fi
  done
fi

if [ -z "$APP_PATH" ] && [ -d /app ]; then
  APP_PATH="$(find /app -maxdepth 2 -type f \( -name 'app_unloadv*.py' -o -name 'app_unload*.py' \) ! -path '/app/backups/*' | sort | tail -n 1 || true)"
fi

if [ -z "$APP_PATH" ]; then
  echo "No app_unload*.py file found." >&2
  echo "APP_FILE=${APP_FILE:-<unset>} PWD=$(pwd)" >&2
  echo "Top-level files in /app:" >&2
  ls -la /app >&2 || true
  exit 1
fi

APP_VERSION="${APP_VERSION:-}"
APP_BUILD="${APP_BUILD:-}"

if [ -z "$APP_VERSION" ]; then
  APP_VERSION="$(grep -m1 -E '^[[:space:]]*_APP_VERSION[[:space:]]*=' "$APP_PATH" | sed -E 's/.*"([^"]+)".*/\1/' || true)"
fi
if [ -z "$APP_BUILD" ]; then
  APP_BUILD="$(grep -m1 -E '^[[:space:]]*_APP_BUILD[[:space:]]*=' "$APP_PATH" | sed -E 's/.*=[[:space:]]*([0-9]+).*/\1/' || true)"
fi
if [ -z "$APP_VERSION" ]; then
  APP_VERSION="unknown"
fi
if [ -z "$APP_BUILD" ]; then
  APP_BUILD="unknown"
fi

echo "Launching Streamlit app: $APP_PATH"
echo "TruckApp version: $APP_VERSION (build $APP_BUILD)"

STREAMLIT_PORT="${STREAMLIT_SERVER_PORT:-8501}"
STREAMLIT_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"

exec streamlit run "$APP_PATH" \
  --server.port="${STREAMLIT_PORT}" \
  --server.address="${STREAMLIT_ADDRESS}" \
  --server.headless=true
