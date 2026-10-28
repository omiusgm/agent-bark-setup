#!/usr/bin/env python3
"""Bark notifications for agents. No automatic monitoring or approvals."""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KINDS = {"question": "🙋 Нужен ответ", "approval": "🔐 Нужно согласование",
         "review": "✅ Готово к проверке", "error": "🚨 Требуется внимание"}
SERVICE = "agent-bark-setup"
ACCOUNT = "bark-device-key"
SERVER = "https://api.day.app/push"
COOLDOWN = 3600
ICONS = {name: f"https://raw.githubusercontent.com/omiusgm/agent-bark-setup/main/icons/{name}.png"
         for name in ("agent", "approval", "question", "complete", "warning", "code", "project", "server")}
ICONS.update({name: f"https://raw.githubusercontent.com/omiusgm/agent-bark-setup/main/icons/{name}-v2.jpg"
              for name in ("hedgehog", "coordinator", "developer", "infrastructure")})
SENDERS = {"codex": "developer", "ezh": "hedgehog", "coordinator": "coordinator",
           "dot": None, "other": None}


def clean(value, name, limit):
    if not isinstance(value, str):
        raise ValueError(f"{name}: нужна строка")
    value = " ".join(value.split())
    if not value or len(value) > limit:
        raise ValueError(f"{name}: длина должна быть от 1 до {limit}")
    return value


def secret():
    if sys.platform == "darwin":
        p = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", SERVICE,
                            "-a", ACCOUNT, "-w"], capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError("Ключ Bark не настроен в Связке ключей")
        key = p.stdout.strip()
    else:
        path = Path.home() / ".config/agent-bark-setup/device-key"
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise RuntimeError("Ключ Bark отсутствует или доступен другим пользователям")
        key = path.read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key):
        raise RuntimeError("Некорректный ключ Bark")
    return key


def notify(kind, project, chat, host, message, event_id, url="", icon="", *, dry_run=False, sender="codex"):
    if kind not in KINDS:
        raise ValueError("Неизвестный тип события")
    project = clean(project, "project", 60)
    chat = clean(chat, "chat", 80)
    host = clean(host, "host", 40)
    message = clean(message, "message", 180)
    event_id = clean(event_id, "event_id", 120)
    payload = {"title": f"{KINDS[kind]} · {project}", "subtitle": f"{chat} · {host}",
               "body": message, "group": project, "isArchive": "1", "level": "active"}
    if sender not in SENDERS:
        raise ValueError("Неизвестная роль отправителя")
    # A role is self-reported metadata, never authentication or an access grant.
    # Legacy icon is intentionally ignored: Codex must not select Ezh's avatar.
    selected_icon = SENDERS[sender]
    if selected_icon:
        payload["icon"] = ICONS[selected_icon]
    if url:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in ("t.me", "telegram.me") or parsed.username or parsed.password or parsed.port or not parsed.path.strip("/"):
            raise ValueError("Допускается только ссылка https://t.me/... или https://telegram.me/...")
        payload["url"] = url
    if dry_run:
        return {"status": "preview", "payload": payload}
    key = secret()  # validate configuration before recording an attempted send
    state_dir = Path.home() / ".local/state/agent-bark-setup"
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    db_path = state_dir / "events.sqlite3"
    fd = os.open(db_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    identity = hashlib.sha256(json.dumps([kind, host, event_id], ensure_ascii=False).encode()).hexdigest()
    with sqlite3.connect(db_path, timeout=5) as db:
        db.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, attempted REAL NOT NULL, status TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT attempted, status FROM events WHERE id=?", (identity,)).fetchone()
        if row and time.time() - row[0] < COOLDOWN:
            return {"status": "duplicate_suppressed", "previous_status": row[1]}
        db.execute("INSERT OR REPLACE INTO events VALUES (?, ?, ?)", (identity, time.time(), "attempted"))
    payload["device_key"] = key
    req = urllib.request.Request(SERVER, data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    status = "uncertain"
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read(65536))
            if response.status == 200 and data.get("code") == 200:
                status = "accepted_by_bark"
            else:
                status = "rejected_by_bark"
    except urllib.error.HTTPError:
        status = "rejected_by_bark"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        pass
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE events SET status=? WHERE id=?", (status, identity))
    return {"status": status, "note": "Приём сервером не подтверждает показ на iPhone; при uncertain не повторяйте вслепую."}
