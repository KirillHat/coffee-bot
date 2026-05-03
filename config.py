"""Configuration loader. Reads environment variables from .env file.

Designed to be tolerant of malformed values: bad entries in ADMIN_IDS or
OWNER_CHAT_ID are logged and skipped instead of crashing the whole bot.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

log = logging.getLogger(__name__)


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            log.warning("ADMIN_IDS: skipping invalid entry %r", chunk)
    return ids


def _parse_int(raw: str | None, default: int = 0, *, name: str = "value") -> int:
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log.warning("%s: invalid integer %r — falling back to %d", name, raw, default)
        return default


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    owner_chat_id: int = 0
    db_path: Path = BASE_DIR / "shop.db"
    currency: str = "USD"
    payment_provider_token: str = ""
    webapp_url: str = ""

    @property
    def payments_enabled(self) -> bool:
        return bool(self.payment_provider_token)

    @property
    def webapp_enabled(self) -> bool:
        return bool(self.webapp_url)

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("BOT_TOKEN")
        if not token or not token.strip():
            raise RuntimeError(
                "BOT_TOKEN is missing. Copy .env.example to .env and fill in the values."
            )

        return cls(
            bot_token=token.strip(),
            admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
            owner_chat_id=_parse_int(
                os.getenv("OWNER_CHAT_ID"), default=0, name="OWNER_CHAT_ID"
            ),
            db_path=BASE_DIR / (os.getenv("DB_FILENAME") or "shop.db").strip(),
            currency=(os.getenv("CURRENCY") or "USD").strip() or "USD",
            payment_provider_token=(os.getenv("PAYMENT_PROVIDER_TOKEN") or "").strip(),
            webapp_url=(os.getenv("WEBAPP_URL") or "").strip(),
        )


config = Config.load()
