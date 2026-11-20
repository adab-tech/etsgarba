# etsgarba – WhatsApp AI assistant

A WhatsApp chatbot (Meta Cloud API) backed by Claude. FastAPI webhook, per-user conversation memory, signature verification, duplicate-delivery protection.

## Setup
1. Create a Meta app with the WhatsApp product; note the **access token**, **phone number ID**, and **app secret**.
2. `cp .env.example .env` and fill in the values (plus `ANTHROPIC_API_KEY`).
3. Install and run:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:get_app --factory --port 8000
   ```
4. Expose it (e.g. `ngrok http 8000`) and set the webhook in Meta to `https://<host>/webhook` with your `WHATSAPP_VERIFY_TOKEN`; subscribe to the `messages` field.

## Behaviour
- Text messages go to Claude; replies are sent back, split if over WhatsApp's 4096-char limit.
- Send `/reset` to clear a conversation.
- Non-text messages get a short "text only" notice.
- `ALLOWED_NUMBERS` restricts who can use the bot (recommended while testing).

## Tests
```bash
python -m pytest
```

## Notes
- History is in-memory and lost on restart; use Redis/a DB for multi-instance deployments.
- The system prompt is configurable via `SYSTEM_PROMPT`.
