-- Custo real por job (tokens + USD, vindos do manifest do motor) e descricao
-- pronta-pra-postar por clipe (gerada pelo LLM junto do gancho).

alter table public.jobs
  add column if not exists cost_usd     real,
  add column if not exists total_tokens int,
  add column if not exists triage_model text,
  add column if not exists judge_model  text;

alter table public.clips
  add column if not exists description text;
