-- Fix: claim_job() retornava uma linha toda-NULL quando a fila estava vazia
-- (UPDATE ... RETURNING INTO deixa o record com NULLs e RETURN devolvia ele).
-- Agora devolve NULL de verdade quando nenhum job foi reivindicado.

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

  if not found then
    return null;   -- fila vazia
  end if;
  return j;
end;
$$;

revoke all on function public.claim_job() from anon, authenticated;
