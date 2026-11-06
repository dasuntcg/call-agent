"""Supabase access for the agent (service role key, server-side only)."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, fields
from datetime import datetime

from supabase import AsyncClient, acreate_client

from prompt import SEED_SETTINGS, BusinessSettings

logger = logging.getLogger("receptionist.db")

SETTINGS_TTL_SECONDS = 60
_SETTINGS_FIELDS = {f.name for f in fields(BusinessSettings)}
_settings_cache: tuple[float, BusinessSettings] | None = None


@dataclass
class CallState:
    """What the agent knows about the call in progress."""

    room: str
    started_at: datetime
    caller_number: str | None = None
    call_id: str | None = None
    lead_id: str | None = None
    lead: dict | None = None


def settings_from_row(row: dict) -> BusinessSettings:
    # Drop columns the agent doesn't use (id, updated_at).
    return BusinessSettings(**{k: v for k, v in row.items() if k in _SETTINGS_FIELDS})


class Database:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    @classmethod
    async def connect(cls) -> Database | None:
        """None when Supabase isn't configured, so local runs still work."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            logger.warning("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set; not saving calls")
            return None
        return cls(await acreate_client(url, key))

    async def fetch_settings(self) -> BusinessSettings | None:
        res = await self._client.table("business_settings").select("*").limit(1).execute()
        return settings_from_row(res.data[0]) if res.data else None

    async def create_call(self, room: str, caller_number: str | None, started_at: datetime) -> str:
        res = (
            await self._client.table("calls")
            .insert(
                {
                    "livekit_room": room,
                    "caller_number": caller_number,
                    "started_at": started_at.isoformat(),
                }
            )
            .execute()
        )
        return res.data[0]["id"]

    async def finish_call(
        self, call_id: str, *, ended_at: datetime, duration_seconds: int, outcome: str
    ) -> None:
        await (
            self._client.table("calls")
            .update(
                {
                    "ended_at": ended_at.isoformat(),
                    "duration_seconds": duration_seconds,
                    "outcome": outcome,
                }
            )
            .eq("id", call_id)
            .execute()
        )

    async def save_lead(self, lead: dict, lead_id: str | None = None) -> str:
        """Insert a lead, or update it when the agent saves again during the call."""
        table = self._client.table("leads")
        if lead_id:
            await table.update(lead).eq("id", lead_id).execute()
            return lead_id
        res = await table.insert(lead).execute()
        return res.data[0]["id"]


async def load_settings(db: Database | None) -> BusinessSettings:
    """Settings for the next call: cached briefly, falling back to SEED_SETTINGS so the
    phone still gets answered if Supabase is down or empty."""
    global _settings_cache
    if _settings_cache and time.monotonic() - _settings_cache[0] < SETTINGS_TTL_SECONDS:
        return _settings_cache[1]
    if db is None:
        return SEED_SETTINGS
    try:
        settings = await db.fetch_settings()
    except Exception:
        logger.exception("failed to load business settings; using fallback")
        return _settings_cache[1] if _settings_cache else SEED_SETTINGS
    if settings is None:
        logger.warning("business_settings table is empty; using fallback")
        return SEED_SETTINGS
    _settings_cache = (time.monotonic(), settings)
    return settings
