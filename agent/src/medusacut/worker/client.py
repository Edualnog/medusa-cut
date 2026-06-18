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
    return data[0] if isinstance(data, list) else data


def update_job(sb, job_id: str, **fields) -> None:
    sb.table("jobs").update(fields).eq("id", job_id).execute()


def get_key_cipher(sb, user_id: str) -> str | None:
    res = sb.table("user_api_keys").select("key_cipher").eq("user_id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0]["key_cipher"] if rows else None


def upload_clip(sb, storage_path: str, local_path: str) -> None:
    with open(local_path, "rb") as fh:
        sb.storage.from_("clips").upload(
            storage_path,
            fh.read(),
            {"content-type": "video/mp4", "upsert": "true"},
        )


def insert_clip(sb, row: dict) -> None:
    sb.table("clips").insert(row).execute()
