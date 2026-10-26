from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from prompt import (
    SEED_SETTINGS,
    BusinessSettings,
    build_greeting,
    build_instructions,
    format_hours,
    is_open,
    next_opening,
)

MELB = ZoneInfo("Australia/Melbourne")

# Fixed example business, so tests don't change when the real seed data does.
EXAMPLE = BusinessSettings(
    business_name="Bayside Plumbing",
    agent_name="Emma",
    greeting=(
        "Hi, thanks for calling Bayside Plumbing. You're speaking with Emma, "
        "an AI assistant, and this call may be recorded or transcribed. "
        "How can I help you today?"
    ),
    timezone="Australia/Melbourne",
    business_hours={
        "mon": ["07:30", "17:00"],
        "tue": ["07:30", "17:00"],
        "wed": ["07:30", "17:00"],
        "thu": ["07:30", "17:00"],
        "fri": ["07:30", "16:00"],
        "sat": ["08:00", "12:00"],
        "sun": None,
    },
    services="Residential plumbing.",
    service_areas="Bayside Melbourne.",
    pricing_guidance="Call-out fee is $99.",
    faqs="Q: Are you licensed? A: Yes.",
    rules="If someone smells gas, tell them to call the gas emergency line first.",
)


def melb(*args: int) -> datetime:
    return datetime(*args, tzinfo=MELB)


# 2026-10-26 is a Monday.
MON_10AM = melb(2026, 10, 26, 10, 0)
MON_6PM = melb(2026, 10, 26, 18, 0)
SAT_1PM = melb(2026, 10, 31, 13, 0)
MON_6AM = melb(2026, 10, 26, 6, 0)


def test_is_open_during_hours():
    assert is_open(EXAMPLE, MON_10AM)


def test_is_closed_after_hours_and_on_sunday():
    assert not is_open(EXAMPLE, MON_6PM)
    assert not is_open(EXAMPLE, melb(2026, 11, 1, 10, 0))


def test_closing_time_is_exclusive():
    assert not is_open(EXAMPLE, melb(2026, 10, 26, 17, 0))
    assert is_open(EXAMPLE, melb(2026, 10, 26, 7, 30))


def test_is_open_converts_from_utc():
    # 23:00 UTC Sunday is 10:00 Monday in Melbourne (AEDT, UTC+11).
    utc = datetime(2026, 10, 25, 23, 0, tzinfo=ZoneInfo("UTC"))
    assert is_open(EXAMPLE, utc)


def test_next_opening():
    assert next_opening(EXAMPLE, MON_6AM) == "today at 7:30am"
    assert next_opening(EXAMPLE, MON_6PM) == "tomorrow at 7:30am"
    # Saturday afternoon: closed Sunday, so Monday.
    assert next_opening(EXAMPLE, SAT_1PM) == "Monday at 7:30am"


def test_next_opening_never_open():
    settings = replace(EXAMPLE, business_hours={})
    assert next_opening(settings, MON_10AM) is None


def test_format_hours():
    hours = format_hours(EXAMPLE)
    assert hours.startswith("Monday 7:30am to 5pm")
    assert "Saturday 8am to 12pm" in hours
    assert hours.endswith("Sunday closed")


def test_example_greeting_kept_as_is():
    assert build_greeting(EXAMPLE) == EXAMPLE.greeting


def test_seed_greeting_has_disclosure():
    assert build_greeting(SEED_SETTINGS) == SEED_SETTINGS.greeting
    assert "AI assistant" in SEED_SETTINGS.greeting


def test_greeting_without_disclosure_gets_one():
    settings = replace(EXAMPLE, greeting="G'day, how can I help?")
    greeting = build_greeting(settings)
    assert greeting.startswith("Hi, you've reached Bayside Plumbing. I'm Emma, an AI assistant")
    assert "recorded or transcribed" in greeting
    assert greeting.endswith("G'day, how can I help?")


def test_instructions_open_without_transfer_number():
    text = build_instructions(EXAMPLE, MON_10AM)
    assert "You are Emma, the AI phone assistant for Bayside Plumbing." in text
    assert "OPEN right now" in text
    assert "Transfers aren't available" in text
    assert "Monday 10am" in text


def test_instructions_open_with_transfer():
    settings = replace(EXAMPLE, transfer_number="+61400000000")
    text = build_instructions(settings, MON_10AM)
    assert "offer to transfer them" in text


def test_instructions_closed():
    text = build_instructions(EXAMPLE, MON_6PM)
    assert "CLOSED right now" in text
    assert "reopens tomorrow at 7:30am" in text
    assert "offer to transfer" not in text


def test_owner_rules_come_last():
    text = build_instructions(EXAMPLE, MON_10AM)
    assert text.rstrip().endswith(EXAMPLE.rules)


def test_instructions_without_optional_fields():
    settings = replace(EXAMPLE, service_areas=None, pricing_guidance=None, faqs=None, rules=None)
    text = build_instructions(settings, MON_10AM)
    assert "Do not discuss prices" in text
    assert "Owner's rules" not in text
