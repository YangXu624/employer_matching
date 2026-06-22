-- Run this in the Supabase SQL Editor (Dashboard → SQL → New query).
-- Employer Match: profiles, seeker passports, async jobs, and storage RLS.

-- Profiles (extends auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  role text not null check (role in ('seeker', 'employer')),
  display_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Employers read seeker profiles for matching"
  on public.profiles for select
  using (
    exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'employer'
    )
    and role = 'seeker'
  );

-- Seeker passports (one row per seeker)
create table if not exists public.seeker_passports (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  status text not null default 'idle'
    check (status in ('idle', 'processing', 'complete', 'failed')),
  scores jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  resume_path text,
  updated_at timestamptz not null default now()
);

alter table public.seeker_passports enable row level security;

create policy "Seekers read own passport"
  on public.seeker_passports for select
  using (auth.uid() = user_id);

create policy "Seekers insert own passport"
  on public.seeker_passports for insert
  with check (auth.uid() = user_id);

create policy "Seekers update own passport"
  on public.seeker_passports for update
  using (auth.uid() = user_id);

create policy "Employers read complete passports"
  on public.seeker_passports for select
  using (
    status = 'complete'
    and exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'employer'
    )
  );

-- Async passport jobs
create table if not exists public.passport_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'complete', 'failed')),
  error text,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);

create index if not exists passport_jobs_user_id_idx on public.passport_jobs (user_id);

alter table public.passport_jobs enable row level security;

create policy "Seekers read own jobs"
  on public.passport_jobs for select
  using (auth.uid() = user_id);

create policy "Seekers insert own jobs"
  on public.passport_jobs for insert
  with check (auth.uid() = user_id);

-- Signup trigger: create profile from auth metadata role
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  user_role text;
  user_name text;
begin
  user_role := coalesce(new.raw_user_meta_data->>'role', 'seeker');
  if user_role not in ('seeker', 'employer') then
    user_role := 'seeker';
  end if;
  user_name := coalesce(
    new.raw_user_meta_data->>'display_name',
    split_part(new.email, '@', 1)
  );
  insert into public.profiles (id, role, display_name)
  values (new.id, user_role, user_name);
  if user_role = 'seeker' then
    insert into public.seeker_passports (user_id, status)
    values (new.id, 'idle')
    on conflict (user_id) do nothing;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Storage bucket for resumes (create bucket named "resumes" in Dashboard if this fails)
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

create policy "Seekers upload own resume"
  on storage.objects for insert
  with check (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Seekers read own resume"
  on storage.objects for select
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Seekers update own resume"
  on storage.objects for update
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Seekers delete own resume"
  on storage.objects for delete
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
