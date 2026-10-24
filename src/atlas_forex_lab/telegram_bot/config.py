"""Environment-based Telegram bot configuration."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class BotConfig:
    token: str
    broker_links: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.getenv("ATLAS_TELEGRAM_BOT_TOKEN", "").strip()
        raw_links = os.getenv("ATLAS_BROKER_LINKS", "").strip()
        links: list[tuple[str, str]] = []
        for item in raw_links.split(";"):
            if not item.strip():
                continue
            parts = item.split("|", 2)
            if len(parts) != 3:
                raise ValueError("ATLAS_BROKER_LINKS entries must be code|Label|https://url")
            code, label, url = (part.strip() for part in parts)
            if not code or not label or not url.startswith("https://"):
                raise ValueError("broker links require code, label and an https URL")
            links.append((label, url))
        return cls(token=token, broker_links=tuple(links))
