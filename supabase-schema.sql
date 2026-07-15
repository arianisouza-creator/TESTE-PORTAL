create table if not exists public.internet_contracts (
  id bigint primary key,
  empresa text not null default '',
  obra text not null default '',
  vencimento text not null default '',
  numero_contrato text not null default '',
  status_contrato text not null default 'Ativo',
  inicio_contrato text not null,
  fim_contrato text not null default '',
  contato text not null default '',
  obs_contrato text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.internet_month_entries (
  month_key text not null,
  contract_id bigint not null references public.internet_contracts (id) on delete cascade,
  status text not null default 'Ativo',
  valor numeric null,
  pedido text not null default '',
  aprovado boolean null,
  s1 boolean null,
  login_acesso text not null default '',
  senha_acesso text not null default '',
  obs text not null default '',
  created_at timestamptz not null default now(),
  primary key (month_key, contract_id)
);

create table if not exists public.internet_lines (
  id bigint primary key,
  month_key text not null,
  numero text not null default '',
  responsavel text not null default '',
  status text not null default 'Ativo',
  centro_custo text not null default '',
  percentual text not null default '',
  created_at timestamptz not null default now()
);

alter table if exists public.internet_lines
add column if not exists status text not null default 'Ativo';

create table if not exists public.diarista_cadastros (
  id bigint primary key,
  obra_diarista text not null default '',
  nome_diarista text not null default '',
  status_diarista text not null default 'Ativo',
  inicio_diarista text not null,
  fim_diarista text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.diarista_month_entries (
  month_key text not null,
  diarista_id bigint not null references public.diarista_cadastros (id) on delete cascade,
  pedido text not null default '',
  valor numeric null,
  protocolado text not null default '',
  link text not null default '',
  created_at timestamptz not null default now(),
  primary key (month_key, diarista_id)
);

create table if not exists public.hitachi_collaborators (
  id bigint primary key,
  month_key text not null,
  empresa text not null default 'MSE ENGENHARIA',
  colaborador text not null default '',
  situacao text not null default 'Ativo',
  holerite text not null default 'OK',
  comprovante_pagamento text not null default 'OK',
  comprovante_adiantamento text not null default 'OK',
  kit_rescisao text not null default 'N/A',
  created_at timestamptz not null default now()
);

create table if not exists public.hitachi_company_docs (
  id bigint primary key,
  month_key text not null,
  empresa text not null default 'MSE ENGENHARIA',
  documento text not null default '',
  status text not null default 'OK',
  created_at timestamptz not null default now()
);

alter table public.internet_contracts enable row level security;
alter table public.internet_month_entries enable row level security;
alter table public.internet_lines enable row level security;
alter table public.diarista_cadastros enable row level security;
alter table public.diarista_month_entries enable row level security;
alter table public.hitachi_collaborators enable row level security;
alter table public.hitachi_company_docs enable row level security;

drop policy if exists "anon_full_internet_contracts" on public.internet_contracts;
create policy "anon_full_internet_contracts"
on public.internet_contracts
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_internet_month_entries" on public.internet_month_entries;
create policy "anon_full_internet_month_entries"
on public.internet_month_entries
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_internet_lines" on public.internet_lines;
create policy "anon_full_internet_lines"
on public.internet_lines
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_diarista_cadastros" on public.diarista_cadastros;
create policy "anon_full_diarista_cadastros"
on public.diarista_cadastros
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_diarista_month_entries" on public.diarista_month_entries;
create policy "anon_full_diarista_month_entries"
on public.diarista_month_entries
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_hitachi_collaborators" on public.hitachi_collaborators;
create policy "anon_full_hitachi_collaborators"
on public.hitachi_collaborators
for all
to anon
using (true)
with check (true);

drop policy if exists "anon_full_hitachi_company_docs" on public.hitachi_company_docs;
create policy "anon_full_hitachi_company_docs"
on public.hitachi_company_docs
for all
to anon
using (true)
with check (true);
