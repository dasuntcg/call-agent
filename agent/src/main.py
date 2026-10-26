"""Agent worker entrypoint. Run with `uv run src/main.py console|dev|start`."""

from __future__ import annotations

import logging
import os

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

from prompt import SEED_SETTINGS
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


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}

    settings = SEED_SETTINGS  # Phase 2: load from Supabase
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
        agent=Receptionist(settings),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=_select_noise_cancellation,
            ),
        ),
    )
    await ctx.connect()
    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
