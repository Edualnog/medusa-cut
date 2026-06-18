-- Medusa Cut · Fase 3 — fila de jobs + clipes.
--
-- Modelo: a web cria um `job` (status=queued); o WORKER (service_role) reivindica
-- com claim_job() (atomico, sem processar em dobro), processa e grava os `clips`.
--
-- RLS: o usuario SO LE (select) os proprios jobs/clips (pra biblioteca + progresso
-- em tempo real). Escrita (insert/update) e so via service_role — web (rotas /api)
-- e worker. Sem policy de escrita => negado pra authenticated/anon.

create table if not exists public.jobs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  source_url  text not null,
  status      text not null default 'queued'
              check (status in ('queued', 'processing', 'done', 'error')),
  progress    real not null default 0,           -- 0..1
  stage       text,                              -- rotulo da etapa atual
  options     jsonb not null default '{}'::jsonb,
  error       text,
  created_at  timestamptz not null default now(),
  started_at  timestamptz,
  finished_at timestamptz
);

create index if not exists jobs_user_idx on public.jobs (user_id, created_at desc);
create index if not exists jobs_queue_idx on public.jobs (status, created_at);

create table if not exists public.clips (
  id             uuid primary key default gen_random_uuid(),
  job_id         uuid not null references public.jobs (id) on delete cascade,
  user_id        uuid not null references auth.users (id) on delete cascade,
  idx            int not null,
  storage_path   text not null,                  -- caminho no bucket 'clips'
  hook           text,
  reason         text,
  virality_score real,
  start_s        real,
  end_s          real,
  duration_s     real,
  created_at     timestamptz not null default now()
);

create index if not exists clips_job_idx on public.clips (job_id, idx);

alter table public.jobs  enable row level security;
alter table public.clips enable row level security;

-- usuario LE os proprios (necessario pra realtime/biblioteca); escrita so service_role
create policy "jobs_select_own"  on public.jobs  for select using (user_id = auth.uid());
create policy "clips_select_own" on public.clips for select using (user_id = auth.uid());

-- reivindicacao atomica de job pelo worker (1 por vez, sem corrida)
create or replace function public.claim_job()
returns public.jobs
language plpgsql
security definer
set search_path = public
as $$
declare
  j public.jobs;
begin
  update public.jobs
     set status = 'processing', started_at = now()
   where id = (
     select id from public.jobs
      where status = 'queued'
      order by created_at
      for update skip locked
      limit 1
   )
  returning * into j;
  return j;   -- NULL se nao houver job na fila
end;
$$;

revoke all on function public.claim_job() from anon, authenticated;

-- bucket privado pros clipes (download via signed URL, gerado no server)
insert into storage.buckets (id, name, public)
values ('clips', 'clips', false)
on conflict (id) do nothing;
