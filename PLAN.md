# AI Phone Receptionist: Build Plan

> **For Claude Code:** This is the master plan for the project. Work through it **one phase at a time**, in order. At the end of each phase, stop, summarise what was built, list anything the human needs to do manually (accounts, keys, dashboard settings), and confirm the acceptance criteria pass before moving on. LiveKit's APIs change often: before writing LiveKit code, check the current docs (https://docs.livekit.io/llms.txt) instead of relying on memory, and pin package versions once things work.

---

## 1. What we're building

An AI agent that answers a business phone line 24/7, has a natural conversation with the caller, answers common questions from the business's own information, captures the inquiry (name, number, what they need), and sends it to the owner straight away. A web dashboard lets the owner see every call and lead and edit what the agent knows, without touching code.

**MVP scope**
- Answers inbound calls on an Australian number
- Greets callers, says it's an AI assistant, and tells them the call may be recorded or transcribed
- Answers FAQs (services, service areas, hours, rough pricing guidance) from business settings
- Captures the inquiry and saves it as a lead
- Transfers to a human on request or when urgent (during business hours)
- After the call, saves the transcript and an AI summary, then emails and texts the owner
- Dashboard: calls, leads, lead status, business settings, and a browser test-call page

**Out of scope for MVP (later phases):** calendar booking, outbound calls, multiple businesses (multi-tenant), CRM sync, call recording audio.

---

## 2. Architecture

```
Caller ──► AU phone number (Twilio)
              │  Elastic SIP Trunk
              ▼
        LiveKit Cloud (SIP → room per call)
              │  dispatch rule → agent_name "receptionist"
              ▼
   Agent worker (Python, LiveKit Agents)  ── hosted on LiveKit Cloud (NOT Vercel)
     STT: Deepgram (en-AU) → LLM: Claude → TTS: Cartesia / ElevenLabs
     VAD: Silero · Turn detection: LiveKit turn detector
     Tools: save_inquiry, transfer_to_human, end_call
              │
              ├──► Supabase (Postgres): settings, calls, leads, transcripts
              └──► Notifications: Resend (email) + Twilio SMS

   Web dashboard (Next.js) ── hosted on Vercel
     Supabase Auth · reads/writes Supabase · issues LiveKit tokens for browser test calls
```

### ⚠️ Key hosting constraint
**The voice agent cannot run on Vercel.** It's a long-running process holding live audio connections for the full length of each call, and Vercel only runs short-lived serverless functions. So:
- **Vercel** hosts the Next.js dashboard and its API routes (token endpoint, webhooks).
- **LiveKit Cloud** hosts the agent worker (`lk agent create` / `lk agent deploy`). It handles scaling, rolling deploys, and logs.
  - LiveKit Cloud agent regions are currently `us-east`, `eu-central` and `ap-south` (Mumbai). **Use `ap-south`**, the closest to Australia.
  - If the latency from Mumbai is noticeable in testing, or customer data must stay in Australia, self-host the same Docker image in Sydney (AWS `ap-southeast-2` or Fly.io `syd`). The agent code doesn't change.

### ⚠️ Phone number constraint
LiveKit's own phone numbers are US-only. **Use a Twilio Australian number**, connected to LiveKit with an Elastic SIP Trunk. Twilio requires an approved Regulatory Bundle (ID, address, ABN) before an AU number activates, which can take days, so **start this in Phase 0**.

---

## 3. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Agent framework | LiveKit Agents (Python, `livekit-agents` 1.5.x) | Use `uv` for dependency management |
| LLM | Claude via `livekit-plugins-anthropic` | Default `claude-haiku-5-5` for speed; switch to `claude-sonnet-5-5` via env var if answers need more reasoning. Enable prompt caching. |
| STT | Deepgram (`livekit-plugins-deepgram`), Nova model, `language="en-AU"` | Australian accent accuracy matters |
| TTS | Cartesia or ElevenLabs | Pick an Australian-accented voice; make the voice ID configurable from settings |
| VAD / turns | Silero VAD + LiveKit turn-detector plugin | Telephony noise cancellation plugin if available on the plan |
| Telephony | Twilio AU number → Elastic SIP Trunk → LiveKit SIP | Region pin telephony to `aus` if offered |
| Database / auth | Supabase (Postgres + Auth), **Sydney region** | Row-level security on |
| Dashboard | Next.js (App Router, TypeScript), Tailwind, shadcn/ui | Deployed on Vercel |
| Email | Resend | Lead notification emails |
| SMS | Twilio Messaging | Lead notification texts to owner |

---

## 4. Repository structure (monorepo)

```
/
├── PLAN.md                 ← this file
├── CLAUDE.md               ← short working rules for Claude Code (create in Phase 1)
├── agent/                  ← Python voice agent (deployed to LiveKit Cloud)
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── livekit.toml        ← created by `lk agent create`
│   ├── .env.example
│   ├── src/
│   │   ├── main.py         ← entrypoint, AgentServer / session setup
│   │   ├── receptionist.py ← Agent class, instructions, tools
│   │   ├── prompt.py       ← builds system prompt from business settings
│   │   ├── db.py           ← Supabase client (service role)
│   │   ├── post_call.py    ← summary generation + notifications
│   │   └── notify.py       ← Resend email + Twilio SMS
│   └── tests/
│       ├── test_prompt.py
│       ├── test_tools.py
│       └── test_conversations.py  ← LiveKit agent testing helpers / scripted scenarios
├── web/                    ← Next.js dashboard (deployed to Vercel)
│   ├── app/
│   │   ├── login/
│   │   ├── dashboard/
│   │   ├── calls/[id]/
│   │   ├── leads/
│   │   ├── settings/
│   │   ├── test-call/
│   │   └── api/
│   │       ├── livekit-token/route.ts
│   │       └── livekit-webhook/route.ts
│   ├── lib/supabase/        ← server + browser clients
│   └── .env.example
└── supabase/
    ├── migrations/          ← SQL migrations (schema below)
    └── seed.sql             ← example business settings
```

---

## 5. Environment variables

**agent/.env** (and as LiveKit Cloud secrets in production)
```
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
ANTHROPIC_API_KEY=
LLM_MODEL=claude-haiku-5-5
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=            # or ELEVENLABS_API_KEY
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=   # server-side only, never in the web client
RESEND_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_SMS_FROM=             # AU number capable of SMS
AGENT_NAME=receptionist
```

**web/.env.local** (and Vercel project env vars)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=   # only used in server routes
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
AGENT_NAME=receptionist
```

Never commit `.env` files. Provide `.env.example` files with every key and no values.

---

## 6. Database schema (Supabase)

```sql
-- Single-tenant for MVP: one row in business_settings.
create table business_settings (
  id uuid primary key default gen_random_uuid(),
  business_name text not null,
  agent_name text not null default 'Emma',
  greeting text not null,                 -- first line spoken
  timezone text not null default 'Australia/Melbourne',
  business_hours jsonb not null,          -- {"mon":["08:00","17:00"], ... "sun":null}
  services text not null,                 -- what the business does
  service_areas text,                     -- suburbs/regions covered
  pricing_guidance text,                  -- what the agent may say about price
  faqs text,                              -- free-text Q&A
  rules text,                             -- never-say / must-do rules
  transfer_number text,                   -- E.164, e.g. +614xxxxxxxx
  transfer_enabled boolean not null default true,
  notify_email text,
  notify_sms text,
  tts_voice_id text,
  updated_at timestamptz not null default now()
);

create table calls (
  id uuid primary key default gen_random_uuid(),
  livekit_room text unique not null,
  caller_number text,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  duration_seconds int,
  outcome text check (outcome in ('lead_captured','answered_question','transferred','hung_up','spam','error')),
  transcript jsonb,                       -- [{role, text, ts}]
  summary text,
  created_at timestamptz not null default now()
);

create table leads (
  id uuid primary key default gen_random_uuid(),
  call_id uuid references calls(id) on delete set null,
  name text,
  phone text,
  email text,
  suburb text,
  service_requested text,
  details text,
  urgency text check (urgency in ('low','normal','urgent')) default 'normal',
  preferred_callback text,
  status text check (status in ('new','contacted','quoted','won','lost')) default 'new',
  notes text,
  created_at timestamptz not null default now()
);

create index on calls (started_at desc);
create index on leads (status, created_at desc);

-- RLS: logged-in dashboard users can read/write; the agent uses the service role key.
alter table business_settings enable row level security;
alter table calls enable row level security;
alter table leads enable row level security;
create policy "auth users all" on business_settings for all to authenticated using (true) with check (true);
create policy "auth users all" on calls for all to authenticated using (true) with check (true);
create policy "auth users all" on leads for all to authenticated using (true) with check (true);
```
Restrict sign-ups in Supabase Auth so only invited users can log in, since the policies above trust any authenticated user.

---

## 7. Agent design

### Call flow
1. A call arrives, LiveKit creates a room, and the agent joins.
2. The agent loads `business_settings` from Supabase (cache for ~60s) and builds the system prompt, including the current local time and whether the business is open.
3. It inserts a `calls` row with the room name and caller number (from SIP participant attributes).
4. It speaks the greeting **immediately** (no LLM round-trip for the first line), including the AI disclosure.
5. The conversation runs: the agent answers questions, gathers details, and calls tools.
6. When the caller hangs up or the agent ends the call, the shutdown callback runs post-call processing.

### System prompt (built in `prompt.py`)
Include:
- Identity: "You are {agent_name}, the AI phone assistant for {business_name}."
- Voice style: short, spoken sentences (1–2 at a time), friendly Australian English, no lists, no markdown, no emojis. Read phone numbers digit by digit and confirm them back.
- Goal: understand what the caller needs, answer from the provided info, and capture a lead for anything needing follow-up.
- Required details to collect: name, best callback number (offer to use the number they're calling from), suburb, what they need, urgency, best time to call back. Email is optional.
- Business info: services, areas, hours, pricing guidance, FAQs.
- Rules: never invent prices, availability or policies not in the info. If unsure, say someone will call back with the details. Never promise a booking. Don't give legal, medical or safety advice.
- Open vs closed behaviour: when open, offer a transfer for urgent matters or on request; when closed, take a message and give the opening hours.
- Spam or sales calls: politely end the call.
- Owner's `rules` field appended last.

### Tools (function calls)
| Tool | Args | Behaviour |
|---|---|---|
| `save_inquiry` | name, phone, suburb, service_requested, details, urgency, preferred_callback, email? | Insert a `leads` row linked to the call. Return a confirmation the agent reads back briefly. Can be called again to update. |
| `transfer_to_human` | reason | Only if `transfer_enabled` and the business is open. Tell the caller they're being connected, then do a SIP cold transfer to `transfer_number`. If it fails, apologise and take a message instead. Set outcome `transferred`. |
| `end_call` | reason | Say goodbye, then hang up and close the session. |

### Post-call (`post_call.py`)
1. Save the full transcript (from session history) and the end time and duration.
2. Generate a 2–4 sentence summary and an outcome classification with Claude (structured JSON output).
3. If a lead exists, send the email (Resend) and SMS (Twilio) to the owner with name, number, suburb, need, urgency, and a dashboard link.
4. If the caller hung up before a lead was saved but gave a number, still notify the owner as a "possible missed lead".
5. Wrap everything in try/except. Post-call failures must be logged and must never crash the worker.

### Latency and reliability requirements
- First greeting under 1.5s after answer. Typical response under ~1s after the caller stops talking.
- Interruptions (barge-in) enabled: the agent stops talking when the caller speaks.
- Keep the system prompt compact and enable Anthropic prompt caching.
- If the LLM or TTS errors mid-call, fall back to: "Sorry, I'm having a technical issue. Can I grab your name and number so someone can call you back?" If that fails too, end gracefully. Always log the error with the room name.
- Maximum call length guard (e.g. 15 min).

---

## 8. Web dashboard (Next.js on Vercel)

| Page | Purpose |
|---|---|
| `/login` | Supabase Auth (magic link or email/password) |
| `/dashboard` | Today's calls, new leads count, latest 10 leads, quick status chips |
| `/leads` | Table: filter by status/urgency, update status, add notes, click to call (`tel:`) |
| `/calls` and `/calls/[id]` | Call list; detail page with summary, chat-style transcript, linked lead |
| `/settings` | Form for every `business_settings` field, including a business-hours editor and voice selector. Changes apply to the **next call**, no redeploy. |
| `/test-call` | Talk to the agent in the browser (LiveKit React components); a server route issues a token and dispatches `AGENT_NAME` |

API routes:
- `POST /api/livekit-token`: authenticated users only. Creates a room, a participant token, and explicit agent dispatch.
- `POST /api/livekit-webhook` (optional): verify the signature, record room started/finished events as a backup for call timing.

Use server components for data fetching. Protect all routes with Supabase middleware.

---

## 9. Build phases

### Phase 0: Accounts and manual setup (human does this; Claude Code lists the steps)
- [ ] LiveKit Cloud project; install the `lk` CLI; `lk cloud auth`
- [ ] Anthropic API key, Deepgram key, Cartesia or ElevenLabs key
- [ ] Supabase project in the **Sydney** region
- [ ] Vercel account linked to the GitHub repo
- [ ] Twilio account; submit the **AU Regulatory Bundle**; buy an AU number (voice + SMS)
- [ ] Resend account with a verified sending domain
- [ ] Fill in the business information for the seed settings

**Done when:** all keys are in local `.env` files and the Twilio bundle is submitted.

### Phase 1: Agent MVP (local, no phone)
- Scaffold `agent/` from the LiveKit Python agent starter, adapted to the structure above.
- Implement `prompt.py` with hardcoded seed settings first.
- Add Deepgram en-AU STT, Claude LLM, TTS, Silero VAD, and turn detection.
- Create `CLAUDE.md` with working rules (run commands, test commands, no secrets in code).
- Test in console mode and the LiveKit Agent Playground.

**Done when:** you can talk to the agent locally, it greets you, answers a question from the seed info, and handles an interruption naturally.

### Phase 2: Supabase and tools
- Write migrations and the seed; apply them to Supabase.
- `db.py`: load settings, create and update the call row, insert leads.
- Implement `save_inquiry` and `end_call`. Load the prompt from DB settings.
- Unit tests for prompt building (open/closed logic, timezone) and tools (mock Supabase).

**Done when:** a local test conversation creates a `calls` row and a correct `leads` row.

### Phase 3: Phone calls
- Twilio: create an Elastic SIP Trunk with origination URI pointing to the LiveKit project's SIP endpoint; attach the AU number.
- LiveKit: create an inbound trunk (with the AU number) and a dispatch rule (individual room per call, prefix `call-`, `roomConfig.agents` = `receptionist`). Save both JSON configs in `agent/telephony/` and document the `lk sip` commands in the README.
- Read the caller number from SIP participant attributes into `calls.caller_number`.
- Deploy the agent to LiveKit Cloud: `lk agent create --region ap-south`, set secrets, `lk agent deploy`.

**Done when:** calling the AU number from a mobile reaches the deployed agent, and the call and lead appear in Supabase.

### Phase 4: Post-call summary and notifications
- Implement `post_call.py` and `notify.py` as described in section 7.

**Done when:** within ~30s of hanging up, the owner receives an email and an SMS with correct lead details, and the call has a transcript and summary.

### Phase 5: Dashboard
- Scaffold `web/` (Next.js, TypeScript, Tailwind, shadcn/ui, Supabase SSR auth).
- Build the pages in section 8, starting with leads and calls, then settings, then test-call.
- Deploy to Vercel and set env vars.

**Done when:** the owner can log in on Vercel, see calls and leads, change the greeting in settings, and hear the new greeting on the next phone call.

### Phase 6: Transfer and business hours
- Implement `transfer_to_human` with SIP transfer and a fallback path.
- Use open/closed logic from `business_hours` and the timezone.

**Done when:** an urgent call during hours transfers to the owner's mobile, and after hours the agent takes a message and states the opening hours.

### Phase 7: Hardening and testing
- Scripted conversation tests covering: a normal inquiry, a pricing question not in the info (must not invent a price), a caller who interrupts constantly, a caller who refuses to give a name, a caller with a strong accent or noisy line (manual), wrong number, spam or sales call, asking "are you a robot?", angry caller asking for a human, a caller spelling a suburb, and a caller giving a number with mistakes then correcting it.
- Error fallbacks, max-duration guard, structured logging with the room name.
- Measure latency (LiveKit metrics) and tune: model choice, endpointing delay, prompt length.

**Done when:** all scenarios pass, and 10 real test calls in a row produce correct leads with no crashes.

### Phase 8: Go live
- Forward the existing business number to the Twilio number. Start with **no-answer / busy / after-hours forwarding only**, then move to all calls once confident.
- Monitor the LiveKit dashboard and Supabase for the first week. Review every transcript and refine the prompt and FAQs.

---

## 10. Compliance and trust (Australia)
- The agent must say it's an AI assistant and that the call may be recorded or transcribed, in the first sentence.
- Handle personal information in line with the Privacy Act / Australian Privacy Principles. Keep Supabase in Sydney, collect only what's needed, and set a retention policy (e.g. delete transcripts after 12 months).
- Update the business privacy policy to mention AI call handling and transcription.
- Recording and consent rules vary by state. Get advice before storing call **audio**, which is out of MVP scope.
- Never let the agent claim to be human if asked.

---

## 11. Rough running costs (to verify at build time)
- LiveKit Cloud agent session minutes: about US$0.01/min, plus LiveKit SIP minutes
- Models (STT + LLM + TTS combined): typically a few US cents per minute
- Twilio: AU number monthly fee, inbound per-minute, and SMS
- Supabase, Vercel, Resend: free tiers likely cover MVP volume

---

## 12. Later phases (not now)
- Calendar booking (Google Calendar / Calendly) with a `check_availability` / `book_slot` tool
- CRM sync (HubSpot, etc.)
- Knowledge base from uploaded documents (pgvector) if the FAQ text gets too large for the prompt
- Multi-tenant (several businesses or numbers), using a `business_id` on every table and per-number dispatch
- Outbound callback calls to missed leads
- SMS follow-up to the caller with a confirmation
