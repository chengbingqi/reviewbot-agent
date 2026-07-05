import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class ReviewBotConfig:
    openai_api_key: str | None
    openai_api_base: str | None
    model_name: str
    rag_db_path: str
    rag_top_k: int
    tool_timeout_seconds: int
    auth_enabled: bool
    auth_token: str
    rate_limit_enabled: bool
    rate_limit_per_minute: int


def _to_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_config() -> ReviewBotConfig:
    load_dotenv()
    return ReviewBotConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE"),
        model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
        rag_db_path=os.getenv("RAG_DB_PATH", "reviewbot_memory.db"),
        rag_top_k=_to_int(os.getenv("RAG_TOP_K"), 3),
        tool_timeout_seconds=_to_int(os.getenv("TOOL_TIMEOUT_SECONDS"), 20),
        auth_enabled=_to_bool(os.getenv("AUTH_ENABLED"), False),
        auth_token=os.getenv("AUTH_TOKEN", "change_me"),
        rate_limit_enabled=_to_bool(os.getenv("RATE_LIMIT_ENABLED"), False),
        rate_limit_per_minute=_to_int(os.getenv("RATE_LIMIT_PER_MINUTE"), 20),
    )


def require_api_key() -> str:
    key = get_config().openai_api_key
    if not key:
        raise ConfigError(
            "OPENAI_API_KEY is not configured. Copy .env.example to .env and fill in your API key."
        )
    return key
