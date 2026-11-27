create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  customer_email text not null,
  amount_cents integer not null,
  status text not null default 'draft',
  stripe_session_id text,
  created_at timestamptz not null default now()
);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  stripe_customer_id text,
  status text not null default 'inactive'
);

alter table public.subscriptions enable row level security;

create policy "own subscription" on public.subscriptions
  for select using (auth.uid() = user_id);
