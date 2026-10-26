"""Builds the receptionist's system prompt and greeting from business settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}


@dataclass
class BusinessSettings:
    """Mirrors the business_settings table (see PLAN.md section 6)."""

    business_name: str
    greeting: str
    services: str
    # {"mon": ["08:00", "17:00"], ..., "sun": None}
    business_hours: dict[str, list[str] | None]
    agent_name: str = "Emma"
    timezone: str = "Australia/Melbourne"
    service_areas: str | None = None
    pricing_guidance: str | None = None
    faqs: str | None = None
    rules: str | None = None
    transfer_number: str | None = None
    transfer_enabled: bool = True
    notify_email: str | None = None
    notify_sms: str | None = None
    tts_voice_id: str | None = None


# Hardcoded business for Phase 1, drafted from connectingbrands.com.au (2026-10-26).
# Replaced by the Supabase row in Phase 2. Hours are an assumption: the website lists none.
SEED_SETTINGS = BusinessSettings(
    business_name="Connecting Brands",
    agent_name="Emma",
    greeting=(
        "Hi, thanks for calling Connecting Brands. You're speaking with Emma, "
        "an AI assistant, and this call may be recorded or transcribed. "
        "How can I help you today?"
    ),
    timezone="Australia/Sydney",
    business_hours={
        "mon": ["08:30", "17:00"],
        "tue": ["08:30", "17:00"],
        "wed": ["08:30", "17:00"],
        "thu": ["08:30", "17:00"],
        "fri": ["08:30", "17:00"],
        "sat": None,
        "sun": None,
    },
    services=(
        "Fleet branding and signage. Main services: fleet vehicle wraps (full wraps, "
        "partial wraps, decals, spot graphics, one-way vision window graphics) for cars, "
        "utes, vans, trucks, refrigerated trucks, EVs, construction equipment and boats; "
        "truck curtain graphics for curtain-siders; fleet truck painting with custom colour "
        "matching; corporate and architectural signage (building signs, illuminated letters, "
        "monument signs, wayfinding, safety signage, window prints); digital displays (indoor "
        "and outdoor LED screens, video walls, interactive displays with cloud content "
        "management); custom large format printing (banners, event and exhibition graphics, "
        "window, floor and building wraps, wallpaper); First Nations vehicle wraps with "
        "authentic Aboriginal and Torres Strait Islander artwork; and fleet branding that "
        "counts toward Reconciliation Action Plan and Indigenous Procurement Policy targets. "
        "Also offers in-house design, 3D mockups, project management for national rollouts, "
        "and digital services: web design, brand design, app development, digital "
        "advertising and AI automation. Works with businesses of every size, from one van to "
        "a thousand trucks. 100% First Nations owned and a Supply Nation registered business."
    ),
    service_areas=(
        "Australia-wide through a national network of certified installers, plus New "
        "Zealand. Sydney head office at 350 Edgar Street, Condell Park NSW. Brisbane at "
        "Unit 1, 31 Warehouse Circuit, Yatala QLD. Albury Wodonga at 1/34 Elkington Road, "
        "West Wodonga VIC. Melbourne team servicing Greater Melbourne. Auckland at 47A "
        "Victoria Street, Onehunga. Mobile installation at the customer's site is available."
    ),
    pricing_guidance=(
        "You may give these rough ranges, always saying the final price depends on the "
        "vehicle, coverage and design and the team will send a detailed quote: partial wraps "
        "from about $500 to $1,500, full van wraps about $2,500 to $4,000, large trucks about "
        "$4,000 to $8,000. Fleet volume discounts, design-production-install packages, "
        "progress payments and finance options are available. Quotes include design, "
        "materials, printing and installation, with extras itemised. Do not give prices for "
        "signage, digital displays, painting, printing or digital services; those are quoted."
    ),
    faqs=(
        "How long do wraps last? Usually 5 to 7 years with proper care, up to 10 with "
        "premium materials. Premium cast vinyl from 3M, Avery Dennison and Arlon, UV and "
        "weather resistant. PVC-free eco options available.\n"
        "Warranty? Typically 3 to 5 years depending on material, covering material defects, "
        "adhesion, premature fading and installation workmanship. Extended options available.\n"
        "How long does it take? From approval, a single vehicle is typically 5 to 7 business "
        "days, a small fleet of 5 to 10 vehicles 2 to 3 weeks, large rollouts are phased. "
        "Installation: partial graphics 2 to 4 hours, van or ute full wraps 1 to 2 days, large "
        "trucks 2 to 3 days. Express service is available for urgent jobs. Nights and "
        "weekends installation can be arranged.\n"
        "Can you install at our site? Yes, mobile installation needs a clean, covered area out "
        "of wind and weather.\n"
        "Design? In-house designers, first concepts within 48 hours, photorealistic 3D "
        "mockups of the actual vehicles, unlimited revisions. Exact brand colour matching. "
        "Vector logo files (AI, EPS, PDF) preferred; they can recreate low-resolution logos.\n"
        "Small businesses? Yes, one vehicle or a whole fleet.\n"
        "Caring for a wrap? Hand wash with mild soap, touchless car washes are fine, avoid "
        "brush washes and pressure washing edges, keep the nozzle 30 centimetres away. "
        "Maintenance and repair programs are available.\n"
        "Who have you worked with? Brands including DHL, Toyota Material Handling, Mainfreight, "
        "Bingo Industries, SES, JAX Tyres and Takeuchi.\n"
        "Email: hello@connectingbrands.com.au. Website: connectingbrands.com.au."
    ),
    rules=(
        "Most callers are businesses. As well as the usual details, ask for their business "
        "name, which service they're after, how many and what type of vehicles or what "
        "signage, where the vehicles are based, and their timeframe. If they have a logo or "
        "brand files, say the team will ask for them by email. Auckland and New Zealand "
        "enquiries are welcome; take the details the same way."
    ),
    transfer_number=None,
    transfer_enabled=True,
)


def _parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def is_open(settings: BusinessSettings, now: datetime) -> bool:
    """Whether the business is open at `now` (any tz-aware datetime)."""
    local = now.astimezone(ZoneInfo(settings.timezone))
    hours = settings.business_hours.get(DAYS[local.weekday()])
    if not hours:
        return False
    start, end = (_parse_hhmm(h) for h in hours)
    return start <= local.time() < end


def _format_time(t: time) -> str:
    suffix = "am" if t.hour < 12 else "pm"
    hour = t.hour % 12 or 12
    return f"{hour}{suffix}" if t.minute == 0 else f"{hour}:{t.minute:02d}{suffix}"


def next_opening(settings: BusinessSettings, now: datetime) -> str | None:
    """A spoken description of when the business next opens, e.g. 'Monday at 7:30am'."""
    local = now.astimezone(ZoneInfo(settings.timezone))
    for offset in range(8):
        day = local + timedelta(days=offset)
        key = DAYS[day.weekday()]
        hours = settings.business_hours.get(key)
        if not hours:
            continue
        start = _parse_hhmm(hours[0])
        if offset == 0 and local.time() >= start:
            continue
        if offset == 0:
            when = "today"
        elif offset == 1:
            when = "tomorrow"
        else:
            when = DAY_NAMES[key]
        return f"{when} at {_format_time(start)}"
    return None


def format_hours(settings: BusinessSettings) -> str:
    parts = []
    for key in DAYS:
        hours = settings.business_hours.get(key)
        if hours:
            start, end = (_format_time(_parse_hhmm(h)) for h in hours)
            parts.append(f"{DAY_NAMES[key]} {start} to {end}")
        else:
            parts.append(f"{DAY_NAMES[key]} closed")
    return ", ".join(parts)


AI_DISCLOSURE = "an AI assistant"


def build_greeting(settings: BusinessSettings) -> str:
    """The first line spoken. Guarantees the AI and recording disclosure is present,
    even if the owner edits the greeting and removes it (PLAN.md section 10)."""
    greeting = settings.greeting.strip()
    lowered = greeting.lower()
    if " ai " in f" {lowered} " and "record" in lowered:
        return greeting
    disclosure = (
        f"Hi, you've reached {settings.business_name}. I'm {settings.agent_name}, "
        f"{AI_DISCLOSURE}, and this call may be recorded or transcribed."
    )
    return f"{disclosure} {greeting}"


def build_instructions(settings: BusinessSettings, now: datetime) -> str:
    local = now.astimezone(ZoneInfo(settings.timezone))
    open_now = is_open(settings, now)
    transfer_available = open_now and settings.transfer_enabled and bool(settings.transfer_number)

    if open_now:
        status = "The business is OPEN right now."
        if transfer_available:
            status += (
                " If the matter is urgent, or the caller asks for a person, offer to transfer them."
            )
        else:
            status += " Transfers aren't available, so take a message instead."
    else:
        reopen = next_opening(settings, now)
        status = (
            "The business is CLOSED right now. Take a message and let the caller know "
            "someone will call them back"
            + (f" when the business reopens {reopen}." if reopen else ".")
        )

    sections = [
        f"You are {settings.agent_name}, the AI phone assistant for {settings.business_name}.",
        "# How you speak\n"
        "You are on a phone call, so talk the way a warm, switched-on receptionist at a "
        "local Australian business would. Keep each turn short: usually one or two "
        "sentences, then let the caller talk. Use contractions and everyday words "
        '("no worries", "sure thing", "let me grab a few details"), and vary how you '
        "phrase things instead of repeating the same lines. React to what the caller "
        "actually said, in a few words of your own, before moving on, rather than generic "
        'lines like "I understand" or "Great question". Don\'t '
        "repeat the caller's whole request back to them, and don't apologise or thank them "
        "more than once. Ask one question at a time, and skip questions they've already "
        "answered. Never use lists, markdown, symbols or emojis. Read phone numbers back "
        "digit by digit in small groups to confirm them. Say prices in words, like "
        "ninety-nine dollars.",
        "# Your goal\n"
        "Work out what the caller needs, answer their questions from the business "
        "information below, and capture their details for anything that needs follow-up. "
        "For follow-up, collect: their name, the best callback number (offer to use the "
        "number they're calling from), where they're located, what they need, how urgent it "
        "is, and the best time to call back. Email is optional.",
        "# Business information\n"
        f"Services: {settings.services}\n"
        f"Service areas: {settings.service_areas or 'Not specified.'}\n"
        f"Opening hours ({settings.timezone}): {format_hours(settings)}\n"
        f"Pricing guidance: {settings.pricing_guidance or 'None. Do not discuss prices.'}\n"
        f"FAQs:\n{settings.faqs or 'None.'}",
        "# Current status\n"
        f"It is {local.strftime('%A')} {_format_time(local.time())} local time. {status}",
        "# Rules\n"
        "Never invent prices, availability, policies or anything else not in the business "
        "information. If you don't know, say someone from the team will call back with the "
        "details. Never promise a booking or a specific arrival time. Don't give legal, "
        "medical or safety advice beyond what the business information says. "
        "If asked, always say you're an AI assistant; never claim to be human. "
        "If the call is spam, a sales pitch or a wrong number, politely end it.",
    ]
    if settings.rules:
        sections.append(f"# Owner's rules\n{settings.rules}")
    return "\n\n".join(sections)
