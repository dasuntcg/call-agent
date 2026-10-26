# CLAUDE.md

AI phone receptionist. `PLAN.md` is the master plan: work one phase at a time, and at the end of each phase stop, summarise, list manual steps for the human, and confirm the acceptance criteria.

## Layout
- `agent/`: Python voice agent (LiveKit Agents), deployed to LiveKit Cloud, never Vercel.
- `web/`: Next.js dashboard on Vercel (Phase 5).
- `supabase/`: migrations and seed (Phase 2).

## Agent commands (run from `agent/`)
- Install: `uv sync`
- Download model files (first run): `uv run --module livekit.agents download-files`
- Talk in the terminal: `uv run src/main.py console`
- Connect to LiveKit Cloud for the browser agent console: `lk agent dev` (hot reload; `uv run src/main.py dev` still works but is deprecated)
- Tests: `uv run pytest`
- Lint and format: `uv run ruff check src tests && uv run ruff format src tests`

## Rules
- Never put secrets in code or commit `.env` files. Every new key goes into the matching `.env.example` with no value.
- LiveKit APIs change often. Before writing LiveKit code, check https://docs.livekit.io/llms.txt or the installed package source in `agent/.venv/lib/python3.12/site-packages/livekit/`, not memory.
- Current pins: `livekit-agents` 1.8.x (the plan said 1.5.x; 1.8 is current). Turn detection uses `inference.TurnDetector` (the turn-detector plugin is deprecated), and AgentSession supplies Silero VAD by default.
- The first spoken line must say it's an AI assistant and that the call may be recorded or transcribed. `prompt.build_greeting` enforces this; don't bypass it.
- Agent modules import each other flat (`from prompt import ...`), because `src/` is the script directory and the pytest `pythonpath`.
- Post-call and notification code must catch and log its errors and never crash the worker.
