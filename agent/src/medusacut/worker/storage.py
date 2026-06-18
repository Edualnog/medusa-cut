"""Storage dos clipes no Cloudflare R2 (S3-compativel, sem custo de egress).

Env (server-only): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET.
`boto3` importado DENTRO das funcoes (dep pesada).
"""

from __future__ import annotations

import os


def _client():
    import boto3  # noqa: PLC0415

    account = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _bucket() -> str:
    return os.environ["R2_BUCKET"]


def upload(key: str, local_path: str, content_type: str = "video/mp4") -> None:
    _client().upload_file(local_path, _bucket(), key, ExtraArgs={"ContentType": content_type})


def delete(keys: list[str]) -> None:
    if not keys:
        return
    _client().delete_objects(
        Bucket=_bucket(), Delete={"Objects": [{"Key": k} for k in keys]}
    )
