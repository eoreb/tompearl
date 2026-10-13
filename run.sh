#!/usr/bin/env bash
# Запуск игры «Fight Tom Pearl»

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Подбор свободного порта (по умолчанию 8080)
PORT=8080
while ss -tuln | grep -q ":$PORT "; do
  PORT=$((PORT + 1))
done

echo "=========================================="
echo "  Запуск Fight Tom Pearl (Undertale Edition)"
echo "  URL: http://localhost:$PORT"
echo "=========================================="

# Запуск локального веб-сервера
python3 -m http.server "$PORT" &
SERVER_PID=$!

# Функция завершения при Ctrl+C
cleanup() {
  echo ""
  echo "Остановка сервера..."
  kill $SERVER_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Открытие в браузере
sleep 0.5
if which xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:$PORT" &
elif which firefox >/dev/null 2>&1; then
  firefox "http://localhost:$PORT" &
fi

# Ожидание
wait $SERVER_PID
