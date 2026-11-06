from datetime import UTC, datetime

import pytest

import db
from db import CallState, load_settings, settings_from_row
from prompt import SEED_SETTINGS
from receptionist import Receptionist

LEAD = {
    "name": "Sam Lee",
    "phone": "0412345678",
    "service_requested": "van wrap",
    "details": "Lee Logistics, 3 Hiace vans, wants them done before March",
    "suburb": "Parramatta",
    "urgency": "normal",
    "preferred_callback": "tomorrow morning",
    "email": None,
}


class FakeDatabase:
    def __init__(self, settings=None, fail=False):
        self.leads: dict[str, dict] = {}
        self.settings = settings
        self.fail = fail
        self.fetches = 0

    async def save_lead(self, lead, lead_id=None):
        if self.fail:
            raise RuntimeError("supabase down")
        lead_id = lead_id or f"lead-{len(self.leads) + 1}"
        self.leads[lead_id] = lead
        return lead_id

    async def fetch_settings(self):
        self.fetches += 1
        if self.fail:
            raise RuntimeError("supabase down")
        return self.settings


def make_call():
    return CallState(room="call-test", started_at=datetime.now(UTC), call_id="call-1")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    db._settings_cache = None
    yield
    db._settings_cache = None


async def test_save_inquiry_inserts_lead_linked_to_call():
    fake, call = FakeDatabase(), make_call()
    result = await Receptionist(SEED_SETTINGS, call, fake).record_inquiry(LEAD)
    assert call.lead_id == "lead-1"
    assert fake.leads["lead-1"] == {**LEAD, "call_id": "call-1"}
    assert "saved" in result.lower()


async def test_save_inquiry_again_updates_same_lead():
    fake, call = FakeDatabase(), make_call()
    agent = Receptionist(SEED_SETTINGS, call, fake)
    await agent.record_inquiry(LEAD)
    await agent.record_inquiry({**LEAD, "phone": "0498765432"})
    assert list(fake.leads) == ["lead-1"]
    assert fake.leads["lead-1"]["phone"] == "0498765432"


async def test_save_inquiry_db_failure_keeps_details_and_does_not_raise():
    call = make_call()
    result = await Receptionist(SEED_SETTINGS, call, FakeDatabase(fail=True)).record_inquiry(LEAD)
    assert call.lead == LEAD
    assert call.lead_id is None
    assert result


async def test_save_inquiry_without_db():
    call = make_call()
    result = await Receptionist(SEED_SETTINGS, call, None).record_inquiry(LEAD)
    assert call.lead == LEAD
    assert "noted" in result.lower()


def test_settings_from_row_ignores_extra_columns():
    row = {
        "id": "abc",
        "updated_at": "2026-10-26T00:00:00Z",
        "business_name": "Test Co",
        "greeting": "Hi",
        "services": "Stuff",
        "business_hours": {"mon": ["09:00", "17:00"]},
    }
    settings = settings_from_row(row)
    assert settings.business_name == "Test Co"
    assert settings.agent_name == "Emma"


async def test_load_settings_without_db_uses_fallback():
    assert await load_settings(None) is SEED_SETTINGS


async def test_load_settings_caches_db_row():
    custom = settings_from_row(
        {"business_name": "Test Co", "greeting": "Hi", "services": "x", "business_hours": {}}
    )
    fake = FakeDatabase(settings=custom)
    assert await load_settings(fake) is custom
    assert await load_settings(fake) is custom
    assert fake.fetches == 1


async def test_load_settings_falls_back_on_error_or_empty_table():
    assert await load_settings(FakeDatabase(fail=True)) is SEED_SETTINGS
    assert await load_settings(FakeDatabase(settings=None)) is SEED_SETTINGS
