"""Shared fixtures.

We build a fresh in-memory SQLite database for every test so they stay
isolated and parallelisable. Each fixture also seeds the 40-product demo
catalog where tests need realistic data.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest_asyncio

# Make the project importable when pytest is run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# config.py expects BOT_TOKEN at import time. Set a dummy one so importing
# any handler (which transitively imports config) doesn't blow up.
os.environ.setdefault("BOT_TOKEN", "0:test")

from database import Database  # noqa: E402  — set env var first
from utils.seed_data import seed_if_empty  # noqa: E402


@pytest_asyncio.fixture
async def db(tmp_path) -> Database:
    """Empty Database with the schema applied."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    await db.connect()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def seeded_db(db) -> Database:
    """Database seeded with the 40-product demo catalog."""
    await seed_if_empty(db)
    return db
