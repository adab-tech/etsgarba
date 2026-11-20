import logging

from anthropic import AsyncAnthropic

from .config import Settings
from .memory import ConversationStore

log = logging.getLogger(__name__)

FALLBACK = "Sorry, I'm having trouble right now. Please try again in a moment."


class Assistant:
    def __init__(self, settings: Settings, store: ConversationStore, client=None):
        self.settings = settings
        self.store = store
        self.client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def reply(self, user: str, text: str) -> str:
        if text.strip().lower() in {"/reset", "reset"}:
            self.store.clear(user)
            return "Conversation cleared. How can I help?"

        self.store.add(user, "user", text)
        try:
            resp = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=self.settings.max_tokens,
                system=self.settings.system_prompt,
                messages=self.store.get(user),
            )
            answer = "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception:
            log.exception("Claude call failed")
            self.store.pop_last(user)  # don't keep an unanswered turn
            return FALLBACK

        if not answer:
            self.store.pop_last(user)
            return FALLBACK
        self.store.add(user, "assistant", answer)
        return answer
