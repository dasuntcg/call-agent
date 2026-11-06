-- Initial schema (PLAN.md section 6). Single-tenant for MVP: one row in business_settings.

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
create index on leads (call_id);

-- Keep business_settings.updated_at current when the dashboard edits it.
create function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger business_settings_updated_at
  before update on business_settings
  for each row execute function set_updated_at();

-- RLS: logged-in dashboard users can read/write; the agent uses the service role key.
-- Restrict sign-ups in Supabase Auth so only invited users can log in.
alter table business_settings enable row level security;
alter table calls enable row level security;
alter table leads enable row level security;
create policy "auth users all" on business_settings for all to authenticated using (true) with check (true);
create policy "auth users all" on calls for all to authenticated using (true) with check (true);
create policy "auth users all" on leads for all to authenticated using (true) with check (true);
