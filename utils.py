# utils.py - Утилиты путей ресурсов для обычной работы и скомпилированного .exe
import sys
import os

def get_asset_path(relative_path):
    """Возвращает корректный путь к ресурсу (работает и в Python-скрипте, и в собранном PyInstaller .exe)"""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)
