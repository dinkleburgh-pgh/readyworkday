#!/usr/bin/env bash

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_FILE="${APP_FILE:-app_unloadv1.5.py}"
VENV_DIR="${VENV_DIR:-venv}"
LOG_DIR="${LOG_DIR:-.data}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/streamlit.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/streamlit.pid}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
STREAMLIT_HOST="${STREAMLIT_HOST:-0.0.0.0}"

info() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

error() {
  printf '[ERROR] %s\n' "$*" >&2
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_privileged() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif have_cmd sudo; then
    sudo "$@"
  else
    return 1
  fi
}

auto_install_python_stack() {
  info "Python 3.10+ not found. Attempting self-heal install..."

  if have_cmd apt-get; then
    run_privileged apt-get update && run_privileged apt-get install -y python3 python3-venv python3-pip
  elif have_cmd dnf; then
    run_privileged dnf install -y python3 python3-pip python3-virtualenv
  elif have_cmd yum; then
    run_privileged yum install -y python3 python3-pip
  elif have_cmd apk; then
    run_privileged apk add --no-cache python3 py3-pip py3-virtualenv
  elif have_cmd zypper; then
    run_privileged zypper --non-interactive install python3 python3-pip python3-virtualenv
  else
    return 1
  fi
}

resolve_python_bin() {
  local candidate
  for candidate in python3 python; do
    if have_cmd "$candidate"; then
      if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

find_latest_app_file() {
  local latest
  latest="$(compgen -G "app_unloadv*.py" | sort -V 2>/dev/null | tail -n 1 || true)"
  if [ -z "$latest" ]; then
    latest="$(compgen -G "app_unloadv*.py" | sort | tail -n 1 || true)"
  fi
  printf '%s' "$latest"
}

is_running_streamlit_pid() {
  local pid="$1"
  if [ -z "$pid" ]; then
    return 1
  fi

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi

  if have_cmd ps; then
    ps -p "$pid" -o args= 2>/dev/null | grep -q "streamlit run"
    return $?
  fi

  return 0
}

mkdir -p "$LOG_DIR"

if [ ! -f "$APP_FILE" ]; then
  FALLBACK_APP="$(find_latest_app_file)"
  if [ -n "$FALLBACK_APP" ] && [ -f "$FALLBACK_APP" ]; then
    warn "Default app file '$APP_FILE' not found. Using '$FALLBACK_APP' instead."
    APP_FILE="$FALLBACK_APP"
  else
    error "No app_unloadv*.py file found. Set APP_FILE manually and rerun."
    exit 1
  fi
fi

if ! PYTHON_BIN="$(resolve_python_bin)"; then
  if ! auto_install_python_stack; then
    error "Unable to auto-install Python. Install Python 3.10+, pip, and venv manually, then rerun."
    exit 1
  fi

  PYTHON_BIN="$(resolve_python_bin)" || {
    error "Python install attempt finished, but Python 3.10+ is still unavailable."
    exit 1
  }
fi

info "Using $("$PYTHON_BIN" --version 2>&1)"

if [ ! -d "$VENV_DIR" ]; then
  info "Creating virtual environment in '$VENV_DIR'..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" || {
    warn "venv creation failed. Trying to install venv tooling..."
    if have_cmd apt-get; then
      run_privileged apt-get update && run_privileged apt-get install -y python3-venv || true
    fi
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  }
elif [ ! -x "$VENV_DIR/bin/python" ]; then
  warn "Broken virtual environment detected at '$VENV_DIR'. Rebuilding..."
  "$PYTHON_BIN" -m venv --clear "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PY" ]; then
  error "Virtual env Python not found at '$VENV_PY'."
  exit 1
fi

info "Upgrading pip tooling..."
"$VENV_PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

if [ -f "requirements.txt" ]; then
  info "Installing requirements..."
  "$VENV_PY" -m pip install --upgrade -r requirements.txt
else
  warn "requirements.txt not found. Installing streamlit only."
  "$VENV_PY" -m pip install --upgrade streamlit
fi

if ! "$VENV_PY" -c "import streamlit" >/dev/null 2>&1; then
  warn "Streamlit import check failed; retrying streamlit install..."
  "$VENV_PY" -m pip install --upgrade streamlit
fi

if [ -f "$PID_FILE" ]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if is_running_streamlit_pid "$EXISTING_PID"; then
    info "Streamlit already running (PID $EXISTING_PID)."
    info "URL: http://localhost:$STREAMLIT_PORT"
    info "Log: $LOG_FILE"
    exit 0
  fi

  warn "Removing stale PID file."
  rm -f "$PID_FILE"
fi

info "Starting Streamlit for '$APP_FILE' on port $STREAMLIT_PORT..."
nohup "$VENV_PY" -m streamlit run "$APP_FILE" \
  --server.port "$STREAMLIT_PORT" \
  --server.address "$STREAMLIT_HOST" \
  --server.headless true \
  >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

sleep 2
if kill -0 "$NEW_PID" >/dev/null 2>&1; then
  info "Streamlit started (PID $NEW_PID)."
  info "URL: http://localhost:$STREAMLIT_PORT"
  info "Log: $LOG_FILE"
  # Auto-open browser
  STREAMLIT_URL="http://localhost:$STREAMLIT_PORT"
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    start "$STREAMLIT_URL"
  elif have_cmd xdg-open; then
    xdg-open "$STREAMLIT_URL"
  elif have_cmd open; then
    open "$STREAMLIT_URL"
  else
    info "Please open $STREAMLIT_URL in your browser."
  fi
else
  error "Streamlit failed to start. Recent log output:"
  tail -n 40 "$LOG_FILE" || true
  exit 1
fi
