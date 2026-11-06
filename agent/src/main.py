"""Agent worker entrypoint. Run with `uv run src/main.py console|dev|start`."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)
from livekit.plugins import anthropic, cartesia, deepgram, noise_cancellation

from db import CallState, Database, load_settings
from receptionist import Receptionist

# .env.local (written by `lk app env -w` / `lk agent create`) loads first so its
# LiveKit values win over any blank placeholders left in .env.
load_dotenv(".env.local")
load_dotenv(".env")

logger = logging.getLogger("receptionist")

AGENT_NAME = os.getenv("AGENT_NAME", "receptionist")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")

server = AgentServer()


def _select_noise_cancellation(params: room_io.NoiseCancellationParams):
    # Phone callers get the model tuned for narrowband telephony audio.
    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        return noise_cancellation.BVCTelephony()
    return noise_cancellation.BVC()


def _caller_number(room: rtc.Room) -> str | None:
    for participant in room.remote_participants.values():
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            return participant.attributes.get("sip.phoneNumber")
    return None


def _outcome(call: CallState) -> str:
    # Phase 4 replaces this with a Claude classification of the transcript.
    return "lead_captured" if call.lead else "hung_up"


async def _start_call(db: Database | None, call: CallState) -> None:
    if db is None:
        return
    try:
        call.call_id = await db.create_call(call.room, call.caller_number, call.started_at)
    except Exception:
        logger.exception("failed to create call row")


async def _finish_call(db: Database | None, call: CallState) -> None:
    if db is None or call.call_id is None:
        return
    ended_at = datetime.now(UTC)
    try:
        await db.finish_call(
            call.call_id,
            ended_at=ended_at,
            duration_seconds=int((ended_at - call.started_at).total_seconds()),
            outcome=_outcome(call),
        )
    except Exception:
        logger.exception("failed to finish call row")


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}

    db = await Database.connect()
    settings = await load_settings(db)
    call = CallState(room=ctx.room.name, started_at=datetime.now(UTC))
    ctx.add_shutdown_callback(lambda: _finish_call(db, call))
    voice = settings.tts_voice_id or os.getenv("CARTESIA_VOICE_ID")

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-AU"),
        llm=anthropic.LLM(model=LLM_MODEL, caching="ephemeral"),
        tts=cartesia.TTS(model="sonic-3", voice=voice) if voice else cartesia.TTS(model="sonic-3"),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
        ),
        # Lets the LLM add Cartesia emotion, pause and spell tags (spoken, never
        # transcribed), so delivery follows the mood of the call.
        expressive=True,
    )

    # A quiet office in the background and keyboard typing while the agent is
    # thinking or running a tool, so silences don't sound dead.
    background_audio = BackgroundAudioPlayer(
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.25),
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.5),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
        ],
    )

    await session.start(
        agent=Receptionist(settings, call, db),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=_select_noise_cancellation,
            ),
        ),
    )
    await ctx.connect()
    call.caller_number = _caller_number(ctx.room)
    await _start_call(db, call)
    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
