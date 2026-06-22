-- Run AFTER migration.sql in Supabase SQL Editor.
-- Adds published employer jobs, sample JD library, and demo seeker roster.

-- Sample JD library (read-only reference jobs)
create table if not exists public.sample_jds (
  id text primary key,
  title text not null,
  body text not null,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

alter table public.sample_jds enable row level security;

create policy "Authenticated users read sample jds"
  on public.sample_jds for select
  to authenticated
  using (true);

-- Employer-published job postings (visible to seekers when published)
create table if not exists public.employer_jobs (
  id uuid primary key default gen_random_uuid(),
  employer_id uuid not null references public.profiles (id) on delete cascade,
  title text not null,
  jd_text text not null,
  weights jsonb not null default '{}'::jsonb,
  status text not null default 'published'
    check (status in ('draft', 'published', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists employer_jobs_status_idx on public.employer_jobs (status, created_at desc);
create index if not exists employer_jobs_employer_idx on public.employer_jobs (employer_id);

alter table public.employer_jobs enable row level security;

create policy "Employers manage own jobs"
  on public.employer_jobs for all
  using (auth.uid() = employer_id)
  with check (auth.uid() = employer_id);

create policy "Seekers read published jobs"
  on public.employer_jobs for select
  using (
    status = 'published'
    and exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'seeker'
    )
  );

create policy "Employers read all published jobs"
  on public.employer_jobs for select
  using (
    exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'employer'
    )
  );

-- Demo seeker roster (seed data; no auth account required)
create table if not exists public.demo_seekers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  scores jsonb not null,
  created_at timestamptz not null default now()
);

alter table public.demo_seekers enable row level security;

create policy "Employers read demo seekers"
  on public.demo_seekers for select
  using (
    exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'employer'
    )
  );

-- Seekers can read employer names on published jobs via employer_jobs join profiles
create policy "Seekers read seeker profiles for job context"
  on public.profiles for select
  using (
    role = 'employer'
    and exists (
      select 1 from public.profiles me
      where me.id = auth.uid() and me.role = 'seeker'
    )
  );

-- Allow seekers to read complete passports for transparency (optional browse peers)
create policy "Seekers read complete peer passports"
  on public.seeker_passports for select
  using (
    status = 'complete'
    and exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'seeker'
    )
  );
