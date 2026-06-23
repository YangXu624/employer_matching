-- JD Storage System: standalone `jobs` table for the no-auth MVP on `main`.
--
-- Run this once in the Supabase SQL Editor (project from your .env).
-- No dependency on an auth `profiles` table. Backend (service_role) is the only
-- reader/writer in v1; the frontend never talks to Supabase directly.

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  title text not null,              -- job label (display name)
  jd_text text not null,            -- full job description body
  weights jsonb not null,           -- flat map: competency_id -> weight (sum ~100)
  competencies jsonb not null,      -- enriched per-competency rows: label + description + weight + matched_level
  score jsonb not null default '{}'::jsonb, -- full /api/score payload (audit / debug)
  status text not null default 'published'
    check (status in ('draft', 'published', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists jobs_status_created_idx
  on public.jobs (status, created_at desc);

-- Keep updated_at fresh on every update.
create or replace function public.set_jobs_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists jobs_set_updated_at on public.jobs;
create trigger jobs_set_updated_at
  before update on public.jobs
  for each row execute function public.set_jobs_updated_at();

-- RLS on, with no public policies in v1: only service_role (backend) can read/write.
alter table public.jobs enable row level security;

-- Example stored shape for `competencies` jsonb (per row):
-- [
--   {
--     "competency_id": "technology",
--     "label": "Technology",
--     "description": "Demand the role places on using tools, software, and systems...",
--     "weight": 19,
--     "matched_level": 3
--   }
-- ]
