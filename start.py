#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fight Tom Pearl (Undertale Edition)
Кроссплатформенный запуск для Windows, Linux и macOS.
"""

import sys
import os
import socket
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer

def find_free_port(start_port=8080):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
            port += 1

def main():
    # Переход в директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    port = find_free_port(8080)
    url = f"http://localhost:{port}"

    print("=" * 55)
    print("  FIGHT TOM PEARL (Undertale Edition)")
    print(f"  ОС: {sys.platform} | Python {sys.version.split()[0]}")
    print(f"  Запуск сервера: {url}")
    print("  Для выхода нажмите Ctrl + C")
    print("=" * 55)

    class GameHTTPHandler(SimpleHTTPRequestHandler):
        def end_headers(self):
            # Отключение кэширования для всегда свежей версии игры
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            super().end_headers()

        def log_message(self, format, *args):
            # Подавление лишнего спама запросов в консоль
            pass

    httpd = HTTPServer(('127.0.0.1', port), GameHTTPHandler)

    # Автоматическое открытие в браузере (работает в Windows, Linux и macOS)
    def open_browser():
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Не удалось открыть браузер автоматически: {e}")
            print(f"Откройте ссылку вручную: {url}")

    timer = threading.Timer(0.5, open_browser)
    timer.daemon = True
    timer.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен. До связи, Вась!")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    main()
