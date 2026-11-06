"""The receptionist Agent: instructions and tools."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

from livekit.agents import Agent, RunContext, function_tool
from livekit.agents.beta import EndCallTool

from db import CallState, Database
from prompt import BusinessSettings, build_greeting, build_instructions

logger = logging.getLogger("receptionist")

Urgency = Literal["low", "normal", "urgent"]


class Receptionist(Agent):
    def __init__(
        self, settings: BusinessSettings, call: CallState, db: Database | None = None
    ) -> None:
        super().__init__(
            instructions=build_instructions(settings, datetime.now(UTC)),
            tools=[
                EndCallTool(
                    extra_description=(
                        "Also call it to politely end spam, sales or wrong-number calls."
                    ),
                    end_instructions="say a short, friendly goodbye",
                    ignore_on_enter=True,
                )
            ],
        )
        self._settings = settings
        self._call = call
        self._db = db

    async def on_enter(self) -> None:
        # Speak the greeting straight away, with no LLM round-trip. It carries the AI
        # and recording disclosure, so the caller can't talk over it.
        self.session.say(build_greeting(self._settings), allow_interruptions=False)

    @function_tool
    async def save_inquiry(
        self,
        context: RunContext,
        name: str,
        phone: str,
        service_requested: str,
        details: str,
        # Required: a default makes the strict schema nullable, which Anthropic rejects
        # alongside an enum.
        urgency: Urgency,
        suburb: str | None = None,
        preferred_callback: str | None = None,
        email: str | None = None,
    ) -> str:
        """Save the caller's enquiry so the team can follow up. Call it once you have at
        least their name, callback number and what they need. Call it again with the full
        set of details if they add or correct anything.

        Args:
            name: Caller's name.
            phone: Best callback number, digits only, e.g. 0412345678.
            service_requested: Short label for what they want, e.g. "van wrap".
            details: Everything else useful for the callback, including business name,
                vehicle count and types, and timeframe.
            urgency: How urgent the matter is. Use "normal" unless the caller says otherwise.
            suburb: Suburb, city or region where they or their vehicles are based.
            preferred_callback: When they'd like to be called back, e.g. "tomorrow morning".
            email: Email address, if they offered one.
        """
        return await self.record_inquiry(
            {
                "name": name,
                "phone": phone,
                "service_requested": service_requested,
                "details": details,
                "suburb": suburb,
                "urgency": urgency,
                "preferred_callback": preferred_callback,
                "email": email,
            }
        )

    async def record_inquiry(self, lead: dict) -> str:
        """Tool logic, separate from the LiveKit decorator so it can be unit tested."""
        self._call.lead = lead
        if self._db is None:
            return "Details noted. Let the caller know the team will be in touch."
        try:
            self._call.lead_id = await self._db.save_lead(
                {**lead, "call_id": self._call.call_id}, self._call.lead_id
            )
        except Exception:
            # The details stay on the call state, so post-call can still notify the owner.
            logger.exception("failed to save lead", extra={"room": self._call.room})
        return "Details saved. Briefly let the caller know the team will be in touch."
