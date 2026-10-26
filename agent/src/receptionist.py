"""The receptionist Agent: instructions and (from Phase 2) tools."""

from __future__ import annotations

from datetime import UTC, datetime

from livekit.agents import Agent

from prompt import BusinessSettings, build_greeting, build_instructions


class Receptionist(Agent):
    def __init__(self, settings: BusinessSettings) -> None:
        super().__init__(instructions=build_instructions(settings, datetime.now(UTC)))
        self._settings = settings

    async def on_enter(self) -> None:
        # Speak the greeting straight away, with no LLM round-trip. It carries the AI
        # and recording disclosure, so the caller can't talk over it.
        self.session.say(build_greeting(self._settings), allow_interruptions=False)
