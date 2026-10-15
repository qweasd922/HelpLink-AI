-- HelpLink AI schema. Paste into Supabase > SQL Editor > Run (safe to re-run).
create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 60),
  skills text[] not null default '{}',
  created_at timestamptz not null default now()
);

alter table public.profiles add column if not exists role text not null default 'reporter' check (role in ('reporter','fixer'));

-- Private emails for fixer alerts. RLS is on with NO policies: only the server-side service key can read this table.
create table if not exists public.fixer_contacts (
  id uuid primary key references public.profiles(id) on delete cascade,
  email text not null
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references public.profiles(id),
  title text not null check (char_length(title) between 3 and 120),
  description text not null default '' check (char_length(description) <= 2000),
  photo_url text,
  category text not null check (category in ('Cleaning','Minor maintenance','Animal welfare','Public facilities','Other')),
  location_name text not null check (char_length(location_name) between 1 and 150),
  latitude double precision check (latitude between -90 and 90),
  longitude double precision check (longitude between -180 and 180),
  status text not null default 'open' check (status in ('open','claimed','in_progress','awaiting_confirmation','resolved','cancelled')),
  claimed_by uuid references public.profiles(id),
  after_photo_url text,
  safety_flags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((latitude is null) = (longitude is null))
);

create table if not exists public.confirmations (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  confirmed_by uuid not null references public.profiles(id),
  decision text not null check (decision in ('confirmed','needs_more_work')),
  created_at timestamptz not null default now()
);

create index if not exists reports_status_created_idx on public.reports(status, created_at desc);
create index if not exists reports_category_idx on public.reports(category);
create index if not exists reports_claimed_by_idx on public.reports(claimed_by);
create index if not exists reports_reporter_idx on public.reports(reporter_id);
create index if not exists confirmations_report_idx on public.confirmations(report_id);

-- Auto-create a profile for each new auth user
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles(id, display_name, role)
  values (new.id, left(coalesce(nullif(trim(new.raw_user_meta_data->>'display_name'), ''), split_part(new.email, '@', 1)), 60),
          case when new.raw_user_meta_data->>'role' = 'fixer' then 'fixer' else 'reporter' end);
  insert into public.fixer_contacts(id, email) values (new.id, new.email);
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists reports_touch on public.reports;
create trigger reports_touch before update on public.reports
  for each row execute function public.touch_updated_at();

-- Row Level Security: clients can READ; all state changes go through the functions below.
alter table public.profiles enable row level security;
alter table public.reports enable row level security;
alter table public.confirmations enable row level security;
alter table public.fixer_contacts enable row level security;

drop policy if exists profiles_read on public.profiles;
create policy profiles_read on public.profiles for select using (true);
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists reports_read on public.reports;
create policy reports_read on public.reports for select using (true);
drop policy if exists reports_insert on public.reports;
create policy reports_insert on public.reports for insert to authenticated
  with check (reporter_id = auth.uid() and status = 'open' and claimed_by is null and after_photo_url is null
    and exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'reporter'));
-- (no UPDATE/DELETE policy on reports => direct client updates are denied)

drop policy if exists confirmations_read on public.confirmations;
create policy confirmations_read on public.confirmations for select to authenticated using (true);
-- (no INSERT policy on confirmations => only review_completion() can write)

-- Race-safe state transitions. Each is ONE atomic UPDATE guarded by status/ownership in WHERE,
-- so two simultaneous claims cannot both succeed.
create or replace function public.claim_report(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'Please sign in.'; end if;
  if not exists (select 1 from profiles where id = auth.uid() and role = 'fixer') then
    raise exception 'Only fixers can claim tasks.';
  end if;
  update reports set status='claimed', claimed_by=auth.uid()
   where id=p_id and status='open' and reporter_id <> auth.uid();
  if not found then raise exception 'This task is no longer available to claim.'; end if;
end $$;

create or replace function public.start_report(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  update reports set status='in_progress' where id=p_id and claimed_by=auth.uid() and status='claimed';
  if not found then raise exception 'Only the assigned volunteer can start a claimed task.'; end if;
end $$;

create or replace function public.release_report(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  update reports set status='open', claimed_by=null
   where id=p_id and claimed_by=auth.uid() and status in ('claimed','in_progress');
  if not found then raise exception 'Only the assigned volunteer can release this task.'; end if;
end $$;

create or replace function public.submit_completion(p_id uuid, p_after_url text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_after_url is null or length(p_after_url) = 0 then raise exception 'An after-photo is required.'; end if;
  update reports set status='awaiting_confirmation', after_photo_url=p_after_url
   where id=p_id and claimed_by=auth.uid() and status in ('claimed','in_progress');
  if not found then raise exception 'Only the assigned volunteer can submit completion.'; end if;
end $$;

create or replace function public.review_completion(p_id uuid, p_decision text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_decision not in ('confirmed','needs_more_work') then raise exception 'Invalid decision.'; end if;
  update reports set status = case when p_decision='confirmed' then 'resolved' else 'in_progress' end
   where id=p_id and reporter_id=auth.uid() and status='awaiting_confirmation';
  if not found then raise exception 'Only the reporter can review a task awaiting confirmation.'; end if;
  insert into confirmations(report_id, confirmed_by, decision) values (p_id, auth.uid(), p_decision);
end $$;

create or replace function public.cancel_report(p_id uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  update reports set status='cancelled' where id=p_id and reporter_id=auth.uid() and status='open';
  if not found then raise exception 'Only the reporter can cancel an open report.'; end if;
end $$;

revoke all on function public.claim_report(uuid), public.start_report(uuid), public.release_report(uuid),
  public.submit_completion(uuid, text), public.review_completion(uuid, text), public.cancel_report(uuid)
  from public, anon;
grant execute on function public.claim_report(uuid), public.start_report(uuid), public.release_report(uuid),
  public.submit_completion(uuid, text), public.review_completion(uuid, text), public.cancel_report(uuid)
  to authenticated;

-- Storage: public-read bucket, users may upload only into their own folder, images <= 5 MB
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('report-photos','report-photos', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do nothing;
drop policy if exists photos_read on storage.objects;
create policy photos_read on storage.objects for select using (bucket_id = 'report-photos');
drop policy if exists photos_upload_own on storage.objects;
create policy photos_upload_own on storage.objects for insert to authenticated
  with check (bucket_id = 'report-photos' and (storage.foldername(name))[1] = auth.uid()::text);
