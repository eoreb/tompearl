# build.py - Скрипт сборки автономного бинарника игры через PyInstaller
import subprocess
import sys
import os

def build():
    sep = ';' if sys.platform == 'win32' else ':'
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--add-data=sprites{sep}sprites",
        f"--add-data=sounds{sep}sounds",
        f"--add-data=PressStart2P.ttf{sep}.",
        "--name=TomPearl",
        "main.py"
    ]
    print("[Build] Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    out_name = "TomPearl.exe" if sys.platform == 'win32' else "TomPearl"
    print(f"\n[Build] Готово! Исполняемый файл создан в папке: dist/{out_name}")

if __name__ == '__main__':
    build()
