"""Worker: escuta a fila do Supabase, processa cada job, sobe os clipes.

Roda na VPS (Docker). So faz chamadas de SAIDA pro Supabase — nao precisa de porta
aberta. Um job por vez (seguro pra VPS pequena); pra escalar, suba outro worker.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

POLL_SEC = float(os.environ.get("WORKER_POLL_SEC", "5"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    from medusacut.llm import load_dotenv

    load_dotenv()  # le agent/.env (SUPABASE_*, KEY_ENCRYPTION_SECRET)
    from medusacut.worker import client

    sb = client.get_client()
    print("[worker] conectado ao Supabase; escutando a fila…", flush=True)

    while True:
        try:
            job = client.claim_job(sb)
        except Exception as exc:  # rede/Supabase instavel: espera e tenta de novo
            print(f"[worker] erro ao buscar job: {exc}", file=sys.stderr, flush=True)
            time.sleep(POLL_SEC)
            continue

        if not job:
            time.sleep(POLL_SEC)
            continue

        print(f"[worker] job {job['id']} -> {job['source_url']}", flush=True)
        try:
            _process(sb, job)
            print(f"[worker] job {job['id']} concluido", flush=True)
        except Exception as exc:
            print(f"[worker] job {job['id']} FALHOU: {exc}", file=sys.stderr, flush=True)
            client.update_job(
                sb, job["id"], status="error", error=str(exc)[:500], finished_at=_now()
            )


def _process(sb, job) -> None:
    from medusacut import pipeline
    from medusacut.worker import client
    from medusacut.worker.crypto import decrypt

    job_id = job["id"]
    user_id = job["user_id"]
    url = job["source_url"]
    opts = job.get("options") or {}

    # 1. decifra a chave da OpenRouter do usuario e injeta no ambiente
    cipher = client.get_key_cipher(sb, user_id)
    if not cipher:
        raise RuntimeError("usuario sem chave de API conectada")
    os.environ["LLM_API_KEY"] = decrypt(cipher)

    workdir = tempfile.mkdtemp(prefix="medusajob_")
    last = [0.0, ""]  # (ultimo update ts, ultimo label) — throttle

    def progress(frac: float, label: str) -> None:
        now = time.time()
        if now - last[0] >= 1.5 or label != last[1]:
            last[0], last[1] = now, label
            try:
                client.update_job(sb, job_id, status="processing", progress=float(frac), stage=label)
            except Exception:
                pass  # nao deixa um update de progresso derrubar o job

    try:
        clips = pipeline.generate_clips(
            url,
            out_dir=workdir,
            max_clips=int(opts.get("max_clips", 6)),
            layout=opts.get("layout", "facecam_top_gameplay_bottom"),
            facecam_auto=bool(opts.get("facecam_auto", True)),
            score_virality=bool(opts.get("score_virality", True)),
            captions=bool(opts.get("captions", True)),
            progress=progress,
        )

        # 2. sobe os clipes e registra
        for c in clips:
            local = os.path.join(workdir, c.file)
            storage_path = f"{user_id}/{job_id}/{c.file}"
            client.upload_clip(sb, storage_path, local)
            client.insert_clip(
                sb,
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "idx": c.index,
                    "storage_path": storage_path,
                    "hook": c.hook or None,
                    "reason": c.reason or None,
                    "virality_score": c.virality_score,
                    "start_s": c.start,
                    "end_s": c.end,
                    "duration_s": c.end - c.start,
                },
            )

        client.update_job(
            sb, job_id, status="done", progress=1.0, stage="Pronto", finished_at=_now()
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        os.environ.pop("LLM_API_KEY", None)  # nao deixa a chave vazar pro proximo job


if __name__ == "__main__":
    raise SystemExit(main())
