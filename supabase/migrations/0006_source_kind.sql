-- Upload direto: o usuario sobe o proprio gameplay (sem depender do YouTube, que
-- bloqueia IP de datacenter). O job passa a ter um TIPO de fonte:
--   'url'    -> source_url e um link http (yt-dlp baixa)   [legado/futuro]
--   'upload' -> source_url e a CHAVE do objeto no R2 (worker baixa do R2)
alter table public.jobs
  add column if not exists source_kind text not null default 'url'
  check (source_kind in ('url', 'upload'));
