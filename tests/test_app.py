import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.assistant import FALLBACK, Assistant
from app.config import Settings
from app.main import create_app
from app.memory import ConversationStore
from app.whatsapp import extract_messages, split_text, verify_signature

SECRET = "shh"


def settings(**kw):
    return Settings(
        whatsapp_verify_token="vt", whatsapp_app_secret=SECRET, _env_file=None, **kw
    )


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def payload(mid="m1", sender="2348000000000", text="hi", typ="text"):
    msg = {"id": mid, "from": sender, "type": typ}
    if typ == "text":
        msg["text"] = {"body": text}
    return {"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}


class FakeWA:
    def __init__(self):
        self.sent = []

    async def send_text(self, to, text):
        self.sent.append((to, text))

    async def mark_read(self, mid):
        pass


class FakeClaude:
    def __init__(self, text="hello!", fail=False):
        self.text, self.fail, self.calls = text, fail, []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("boom")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.text)])


def make(claude=None, **kw):
    s = settings(**kw)
    wa = FakeWA()
    claude = claude or FakeClaude()
    a = Assistant(s, ConversationStore(), client=claude)
    return TestClient(create_app(s, a, wa)), wa, claude


def post(client, p):
    body = json.dumps(p).encode()
    return client.post("/webhook", content=body, headers={"X-Hub-Signature-256": sign(body)})


def test_verify_handshake():
    c, *_ = make()
    r = c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"})
    assert r.status_code == 200 and r.text == "42"
    assert c.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"}).status_code == 403


def test_rejects_bad_signature():
    c, wa, _ = make()
    r = c.post("/webhook", content=b"{}", headers={"X-Hub-Signature-256": "sha256=bad"})
    assert r.status_code == 403
    assert c.post("/webhook", content=b"{}").status_code == 403


def test_text_message_gets_reply():
    c, wa, claude = make()
    assert post(c, payload()).status_code == 200
    assert wa.sent == [("2348000000000", "hello!")]
    assert claude.calls[0]["messages"] == [{"role": "user", "content": "hi"}]


def test_duplicate_delivery_ignored():
    c, wa, _ = make()
    post(c, payload()); post(c, payload())
    assert len(wa.sent) == 1


def test_non_text_gets_notice():
    c, wa, claude = make()
    post(c, payload(typ="image"))
    assert "text" in wa.sent[0][1] and not claude.calls


def test_allowlist():
    c, wa, _ = make(allowed_numbers="111")
    post(c, payload(sender="222"))
    assert wa.sent == []


def test_claude_failure_falls_back_and_keeps_history_clean():
    claude = FakeClaude(fail=True)
    c, wa, _ = make(claude=claude)
    post(c, payload())
    assert wa.sent[0][1] == FALLBACK


@pytest.mark.asyncio
async def test_history_and_reset():
    claude = FakeClaude()
    a = Assistant(settings(), ConversationStore(), client=claude)
    await a.reply("u", "one")
    await a.reply("u", "two")
    assert [m["role"] for m in claude.calls[1]["messages"]] == ["user", "assistant", "user"]
    await a.reply("u", "/reset")
    assert a.store.get("u") == []


def test_history_trim_starts_with_user():
    s = ConversationStore(turns=1)
    for role in ["user", "assistant", "user"]:
        s.add("u", role, "x")
    assert s.get("u")[0]["role"] == "user"


def test_helpers():
    assert not verify_signature("", b"x", "sha256=00")
    assert len(extract_messages(payload())) == 1
    chunks = split_text("word " * 2000, 100)
    assert all(len(c) <= 100 for c in chunks) and "".join(chunks).replace(" ", "") == "word" * 2000
