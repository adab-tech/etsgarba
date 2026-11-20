from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    graph_api_version: str = "v21.0"

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    max_tokens: int = 1024
    history_turns: int = 10
    system_prompt: str = (
        "You are a friendly, concise assistant chatting on WhatsApp. "
        "Reply in the same language the user writes in (English or Hausa). "
        "Keep answers short and use plain text; avoid markdown headings and tables."
    )

    allowed_numbers: str = ""

    @property
    def allowed_set(self) -> set[str]:
        return {n.strip() for n in self.allowed_numbers.split(",") if n.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
