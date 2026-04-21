#!/usr/bin/env bash
# ─────────────────────────────────────────────
# CS-Controle 360 — script de inicialização
# Uso: ./run.sh
# ─────────────────────────────────────────────
set -e

# Carrega variáveis de ambiente se existir .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Verifica se uvicorn está disponível
PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

port_is_free() {
  "$PYTHON_BIN" - "$1" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
try:
    s.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

find_frontend_port() {
  local port="$1"
  local tries=0
  while [ "$tries" -lt 20 ]; do
    if port_is_free "$port"; then
      printf '%s' "$port"
      return 0
    fi
    port=$((port + 1))
    tries=$((tries + 1))
  done
  return 1
}

FRONTEND_PORT="$(find_frontend_port "$FRONTEND_PORT")"
if [ -z "$FRONTEND_PORT" ]; then
  echo "❌ Não foi possível encontrar uma porta livre para o frontend."
  exit 1
fi

echo "🚀 Iniciando CS-Controle 360..."
echo "   Backend:  http://127.0.0.1:${BACKEND_PORT}"
echo "   Frontend: http://127.0.0.1:${FRONTEND_PORT}"
echo "   Pressione Ctrl+C para parar"
echo ""

cleanup() {
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

"$PYTHON_BIN" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

(
  cd frontend
  npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort
) &
FRONTEND_PID=$!

wait -n "$BACKEND_PID" "$FRONTEND_PID"
