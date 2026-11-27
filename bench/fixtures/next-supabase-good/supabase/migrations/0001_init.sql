create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  amount_cents integer not null,
  status text not null default 'draft',
  stripe_session_id text
);
alter table public.invoices enable row level security;
create policy "own invoices" on public.invoices for select using (auth.uid() = user_id);

create table public.stripe_events (id text primary key, received_at timestamptz not null default now());
alter table public.stripe_events enable row level security;
