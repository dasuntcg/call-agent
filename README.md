# AI Phone Receptionist

An AI agent that answers a business phone line, answers FAQs from the business's own information, captures leads and notifies the owner. See [PLAN.md](PLAN.md) for the full design and build phases.

## Status
- [x] Phase 1: agent MVP (local, no phone), using hardcoded seed settings in `agent/src/prompt.py`
- [ ] Phase 2: Supabase and tools
- [ ] Phase 3: phone calls
- [ ] Phase 4: post-call summary and notifications
- [ ] Phase 5: dashboard
- [ ] Phase 6: transfer and business hours
- [ ] Phase 7: hardening and testing
- [ ] Phase 8: go live

## Running the agent locally

Requires [uv](https://docs.astral.sh/uv/) and, for the Playground, the [LiveKit CLI](https://docs.livekit.io/home/cli/) (`lk`).

```bash
cd agent
cp .env.example .env        # fill in LiveKit, Anthropic, Deepgram and Cartesia keys
uv sync
uv run --module livekit.agents download-files

uv run src/main.py console  # talk to it from your terminal mic and speakers
lk agent dev                # or connect to LiveKit Cloud and talk in the browser agent console
                            # (without the lk CLI: uv run src/main.py dev, deprecated)
uv run pytest               # unit tests
```

The agent registers under the name in `AGENT_NAME` (default `receptionist`), so in the Playground pick that agent to dispatch it.
