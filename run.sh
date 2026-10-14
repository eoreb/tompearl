#!/usr/bin/env bash
# Запуск игры Fight Tom Pearl на Linux
set -e

cd "$(dirname "$0")"

if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python main.py "$@"
fi

exec python3 start.py "$@"
