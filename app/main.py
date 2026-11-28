import json
import logging
from collections import OrderedDict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .assistant import Assistant
from .config import Settings, get_settings
from .memory import ConversationStore
from .whatsapp import WhatsAppClient, extract_messages, verify_signature

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

UNSUPPORTED = "I can only read text messages for now. Please type your question."


def create_app(
    settings: Settings | None = None,
    assistant: Assistant | None = None,
    wa: WhatsAppClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    wa = wa or WhatsAppClient(settings)
    assistant = assistant or Assistant(settings, ConversationStore(settings.history_turns))
    seen: OrderedDict[str, None] = OrderedDict()  # dedupe Meta's webhook retries

    app = FastAPI(title="etsgarba WhatsApp assistant")
    web_dir = Path(__file__).resolve().parent.parent / "web"

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/webhook")
    async def verify(
        mode: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        challenge: str = Query("", alias="hub.challenge"),
    ):
        if (
            mode == "subscribe"
            and settings.whatsapp_verify_token
            and token == settings.whatsapp_verify_token
        ):
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(403, "verification failed")

    async def handle(msg: dict):
        sender = msg["from"]
        await wa.mark_read(msg["id"])
        if msg["type"] != "text" or not msg["text"].strip():
            await wa.send_text(sender, UNSUPPORTED)
            return
        await wa.send_text(sender, await assistant.reply(sender, msg["text"]))

    @app.post("/webhook")
    async def receive(request: Request, background: BackgroundTasks):
        body = await request.body()
        if not verify_signature(
            settings.whatsapp_app_secret, body, request.headers.get("X-Hub-Signature-256")
        ):
            raise HTTPException(403, "bad signature")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(400, "invalid json")

        allowed = settings.allowed_set
        for msg in extract_messages(payload):
            if not msg["id"] or not msg["from"] or msg["id"] in seen:
                continue
            seen[msg["id"]] = None
            if len(seen) > 5000:
                seen.popitem(last=False)
            if allowed and msg["from"] not in allowed:
                log.info("ignoring non-allowlisted sender")
                continue
            background.add_task(handle, msg)
        return {"status": "ok"}  # always 200 fast so Meta doesn't retry

    app.mount("/static", StaticFiles(directory=web_dir / "static"), name="web_static")

    @app.get("/", include_in_schema=False)
    async def website_home():
        return FileResponse(web_dir / "index.html")

    @app.get("/{page:path}", include_in_schema=False)
    async def website_page(page: str):
        if page not in {"a-propos", "direction", "services", "contact"}:
            raise HTTPException(404, "page not found")
        return FileResponse(web_dir / "index.html")

    return app


def get_app() -> FastAPI:
    return create_app()
