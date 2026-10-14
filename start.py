#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный лаунчер для Fight Tom Pearl (Windows / Linux / macOS).
Автоматически проверяет наличие pygame-ce и запускает нативную игру в отдельном окне.
"""

import sys
import os
import subprocess

def main():
    game_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(game_dir)

    # 1. Проверяем, установлен ли pygame в текущем интерпретаторе
    try:
        import pygame
        # Запускаем игру напрямую
        subprocess.run([sys.executable, "main.py"] + sys.argv[1:])
        return
    except ImportError:
        pass

    # 2. Проверяем наличие виртуального окружения .venv
    venv_py = os.path.join(game_dir, ".venv", "Scripts", "python.exe") if sys.platform == "win32" \
        else os.path.join(game_dir, ".venv", "bin", "python")

    if os.path.exists(venv_py):
        subprocess.run([venv_py, "main.py"] + sys.argv[1:])
        return

    # 3. Если ничего нет, автоматически разворачиваем .venv на первом запуске
    print("=" * 60)
    print("  FIGHT TOM PEARL (Undertale Edition)")
    print("  Первый запуск: настройка окружения (установка pygame-ce)...")
    print("=" * 60)

    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        pip_bin = os.path.join(game_dir, ".venv", "Scripts", "pip.exe") if sys.platform == "win32" \
            else os.path.join(game_dir, ".venv", "bin", "pip")
        subprocess.run([pip_bin, "install", "-r", "requirements.txt"], check=True)
        print("Настройка завершена! Запуск игры...")
        subprocess.run([venv_py, "main.py"] + sys.argv[1:])
    except Exception as e:
        print(f"Ошибка автоматической настройки: {e}")
        print("Попробуйте вручную запустить: pip install -r requirements.txt && python main.py")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()
