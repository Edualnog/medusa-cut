"""Acesso ao Supabase pelo worker (service_role). Tudo server-side."""

from __future__ import annotations

import os


def get_client():
    from supabase import create_client  # noqa: PLC0415

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ausentes no worker")
    return create_client(url, key)


def claim_job(sb):
    """Reivindica 1 job da fila (atomico). Devolve dict do job ou None."""
    data = sb.rpc("claim_job", {}).execute().data
    if not data:
        return None
    job = data[0] if isinstance(data, list) else data
    # defesa: fila vazia pode vir como linha toda-NULL (ver migration 0003)
    if not job or not job.get("id"):
        return None
    return job


def update_job(sb, job_id: str, **fields) -> None:
    sb.table("jobs").update(fields).eq("id", job_id).execute()


def get_key_cipher(sb, user_id: str) -> str | None:
    res = sb.table("user_api_keys").select("key_cipher").eq("user_id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0]["key_cipher"] if rows else None


def upload_clip(sb, storage_path: str, local_path: str) -> None:
    from medusacut.worker import storage  # R2 (Cloudflare)

    storage.upload(storage_path, local_path)


def insert_clip(sb, row: dict) -> None:
    sb.table("clips").insert(row).execute()


# Limite de storage: quantos clipes manter por usuario (Supabase Storage e caro
# pra video; em producao migrar pra Cloudflare R2). Ajustavel por env.
CLIP_CAP = int(os.environ.get("WORKER_CLIP_CAP", "24"))


def enforce_clip_cap(sb, user_id: str, cap: int | None = None) -> None:
    """Apaga (Storage + banco) os clipes do usuario alem dos `cap` mais recentes."""
    cap = cap or CLIP_CAP
    rows = (
        sb.table("clips")
        .select("id, storage_path, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    extra = rows[cap:]
    if not extra:
        return
    paths = [r["storage_path"] for r in extra]
    ids = [r["id"] for r in extra]
    try:
        from medusacut.worker import storage  # R2 (Cloudflare)

        storage.delete(paths)
    except Exception:
        pass
    for i in range(0, len(ids), 50):
        sb.table("clips").delete().in_("id", ids[i : i + 50]).execute()
