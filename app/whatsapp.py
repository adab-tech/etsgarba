import hashlib
import hmac
import logging

import httpx

from .config import Settings

log = logging.getLogger(__name__)
MAX_LEN = 4096  # WhatsApp text message limit


def verify_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def extract_messages(payload: dict) -> list[dict]:
    """Flatten a webhook payload into [{id, from, type, text}]."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []) or []:
                out.append(
                    {
                        "id": m.get("id"),
                        "from": m.get("from"),
                        "type": m.get("type"),
                        "text": (m.get("text") or {}).get("body", ""),
                    }
                )
    return out


def split_text(text: str, limit: int = MAX_LEN) -> list[str]:
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


class WhatsAppClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.s = settings
        self.http = http or httpx.AsyncClient(timeout=15)
        self.url = (
            f"https://graph.facebook.com/{settings.graph_api_version}/"
            f"{settings.whatsapp_phone_number_id}/messages"
        )
        self.headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}

    async def send_text(self, to: str, text: str) -> None:
        for chunk in split_text(text):
            r = await self.http.post(
                self.url,
                headers=self.headers,
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": chunk},
                },
            )
            if r.status_code >= 400:
                log.error("WhatsApp send failed %s: %s", r.status_code, r.text)
                return

    async def mark_read(self, message_id: str) -> None:
        try:
            await self.http.post(
                self.url,
                headers=self.headers,
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
        except httpx.HTTPError:
            log.warning("mark_read failed", exc_info=True)
