#!/usr/bin/env python3
"""One-use localhost-only credential handoff, no secret in arguments or logs."""
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import urllib.parse
import webbrowser

if sys.platform != "darwin" and not sys.platform.startswith("linux"):
    sys.exit("Поддерживаются macOS и Linux.")

TOKEN = secrets.token_urlsafe(32)
PATH = "/" + TOKEN

def page(message=""):
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Подключение Bark</title><style>body{{font:17px -apple-system,BlinkMacSystemFont,sans-serif;background:#f6f7fa;color:#20232a;margin:0}}main{{max-width:570px;margin:8vh auto;padding:32px;background:white;border-radius:20px;box-shadow:0 10px 40px #0001}}input{{box-sizing:border-box;width:100%;font-size:17px;padding:14px;border:1px solid #9ca3af;border-radius:8px}}button{{background:#275ae8;color:white;border:0;border-radius:8px;font-size:17px;padding:13px 20px;margin-top:18px;cursor:pointer}}small{{color:#535d6b}}</style></head><body><main><h1>🔔 Подключение Bark</h1><p>Вставьте ключ или пример ссылки из приложения Bark на iPhone.</p><p><small>Страница доступна только на этом компьютере. На Mac ключ сохраняется в Связке ключей, на Linux — в приватном файле.</small></p><form action="{PATH}" method="post"><label for="key">Ключ или ссылка Bark</label><p><input id="key" name="key" type="password" autocomplete="off" required autofocus></p><button type="submit">Сохранить ключ</button></form><p>{html.escape(message)}</p></main></body></html>'''.encode()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send_page(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def allowed(self):
        return self.path == PATH and self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
    def do_GET(self):
        if not self.allowed(): return self.send_page(b"Not found", 404)
        self.send_page(page())
    def do_POST(self):
        if not self.allowed() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
            return self.send_page(b"Forbidden", 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 2048: raise ValueError()
            values = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
            value = values["key"][0].strip()
            if value.startswith("https://"):
                parsed = urllib.parse.urlsplit(value)
                if parsed.hostname not in ("api.day.app", "day.app") or parsed.username or parsed.password or parsed.port:
                    raise ValueError()
                value = parsed.path.strip("/").split("/")[0]
            if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", value): raise ValueError()
        except (KeyError, UnicodeError, ValueError):
            return self.send_page(page("Ключ или ссылка не распознаны. Проверьте и попробуйте ещё раз."), 400)
        try:
            if sys.platform == "darwin":
                command = f'add-generic-password -s agent-bark-setup -a bark-device-key -w {value}\n'
                subprocess.run(["/usr/bin/security", "-i"], input=command, text=True, capture_output=True)
                check = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", "agent-bark-setup", "-a", "bark-device-key", "-w"], capture_output=True, text=True)
                if check.returncode or check.stdout.strip() != value: raise OSError()
            else:
                folder = Path.home() / ".config/agent-bark-setup"
                folder.mkdir(mode=0o700, parents=True, exist_ok=True)
                if folder.is_symlink() or folder.stat().st_mode & 0o077: raise OSError()
                fd = os.open(folder / "device-key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f: f.write(value)
        except OSError:
            return self.send_page(page("Не удалось сохранить ключ. Возможно, запись уже существует; она не заменена."), 409)
        self.send_page('<!doctype html><html lang="ru"><meta charset="utf-8"><title>Готово</title><body style="font:18px -apple-system;margin:10vh auto;max-width:550px"><h1>✅ Ключ сохранён</h1><p>Можете закрыть вкладку и вернуться к инструкции.</p></body></html>'.encode())
        print("Ключ сохранён; локальная страница закрыта.", flush=True)
        threading.Thread(target=self.server.shutdown, daemon=True).start()

server = HTTPServer(("127.0.0.1", 0), Handler)
address = f"http://127.0.0.1:{server.server_port}{PATH}"
if not webbrowser.open(address):
    sys.exit("Не удалось открыть браузер.")
print("Одноразовая страница открыта в браузере на этом Mac.", flush=True)
timer = threading.Timer(600, server.shutdown)
timer.daemon = True
timer.start()
try:
    server.serve_forever()
finally:
    timer.cancel()
    server.server_close()
