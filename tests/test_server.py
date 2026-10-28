import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bark_server as p

ARGS = dict(kind="question", project="Доступы", chat="Тест", host="Mac", message="Нужен ответ", event_id="event-1")

class Response:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size): return b'{"code":200}'

class PilotTests(unittest.TestCase):
    def test_preview_and_url_validation(self):
        r = p.notify(**ARGS, dry_run=True, url="https://t.me/example")
        self.assertEqual(r["payload"]["group"], "Доступы")
        self.assertNotIn("device_key", r["payload"])
        r = p.notify(**ARGS, sender="ezh", dry_run=True)
        self.assertTrue(r["payload"]["icon"].endswith("/hedgehog-v2.jpg"))
        with self.assertRaises(ValueError):
            p.notify(**ARGS, dry_run=True, url="https://t.me.evil.example/x")
        with self.assertRaises(ValueError):
            p.notify(**dict(ARGS, kind="spam"), dry_run=True)

    def test_role_selects_avatar_and_legacy_icon_cannot_impersonate_ezh(self):
        codex = p.notify(**ARGS, sender="codex", icon="hedgehog", dry_run=True)
        self.assertTrue(codex["payload"]["icon"].endswith('/developer-v2.jpg'))
        for sender in ('dot', 'other'):
            payload = p.notify(**ARGS, sender=sender, icon='hedgehog', dry_run=True)['payload']
            self.assertNotIn('icon', payload)
        coordinator = p.notify(**dict(ARGS, host='Linux'), sender='coordinator', dry_run=True)
        self.assertTrue(coordinator['payload']['icon'].endswith('/coordinator-v2.jpg'))
        with self.assertRaises(ValueError):
            p.notify(**ARGS, sender='admin', dry_run=True)

    def test_dedup_and_server_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}), \
             patch.object(p, "secret", return_value="testkey123"), \
             patch.object(p.urllib.request, "urlopen", return_value=Response()) as send:
            self.assertEqual(p.notify(**ARGS)["status"], "accepted_by_bark")
            self.assertEqual(p.notify(**ARGS)["status"], "duplicate_suppressed")
            self.assertEqual(send.call_count, 1)
            request = send.call_args.args[0]
            self.assertEqual(json.loads(request.data)["device_key"], "testkey123")
            db = Path(tmp) / ".local/state/agent-bark-setup/events.sqlite3"
            self.assertEqual(db.stat().st_mode & 0o077, 0)

    def test_ambiguous_send_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}), \
             patch.object(p, "secret", return_value="testkey123"), \
             patch.object(p.urllib.request, "urlopen", side_effect=TimeoutError()) as send:
            self.assertEqual(p.notify(**ARGS)["status"], "uncertain")
            self.assertEqual(p.notify(**ARGS)["status"], "duplicate_suppressed")
            self.assertEqual(send.call_count, 1)

if __name__ == "__main__": unittest.main()
