-- Prova de aceite dos termos/privacidade (compliance LGPD).
-- Cada aceite vira UMA linha (trilha de auditoria): quem, qual versão, quando.
-- O app grava usando a sessão do próprio usuário (JWT); RLS garante que ele só
-- insere/lê os próprios registros. Sem update/delete -> registros imutáveis.

create table if not exists public.legal_acceptances (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  version     text not null,                       -- LEGAL_VERSION aceita (ex.: 2026-06-18)
  accepts     jsonb not null default '{}'::jsonb,  -- {terms, privacy, content, age}
  app_version text,                                -- versão do app no momento do aceite
  accepted_at timestamptz not null default now()
);

create index if not exists legal_acceptances_user_idx
  on public.legal_acceptances (user_id, accepted_at desc);

alter table public.legal_acceptances enable row level security;

-- usuário só insere/lê os próprios aceites; sem policy de update/delete (imutável)
create policy "la_insert_own" on public.legal_acceptances
  for insert to authenticated with check (user_id = auth.uid());
create policy "la_select_own" on public.legal_acceptances
  for select to authenticated using (user_id = auth.uid());
