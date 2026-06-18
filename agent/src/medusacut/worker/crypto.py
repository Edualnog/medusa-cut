"""Decifra a chave de API do usuario — compativel com o web (lib/crypto.ts).

Formato: "iv:tag:ciphertext" (base64), AES-256-GCM, IV de 12 bytes, tag de 16.
O segredo (KEY_ENCRYPTION_SECRET) e o MESMO da web — server-side only.
"""

from __future__ import annotations

import base64
import os


def _key() -> bytes:
    secret = os.environ.get("KEY_ENCRYPTION_SECRET")
    if not secret:
        raise RuntimeError("KEY_ENCRYPTION_SECRET ausente no ambiente do worker")
    raw = bytes.fromhex(secret) if len(secret) == 64 else base64.b64decode(secret)
    if len(raw) != 32:
        raise ValueError("KEY_ENCRYPTION_SECRET precisa ter 32 bytes (base64 ou hex)")
    return raw


def decrypt(blob: str) -> str:
    """Decifra o blob 'iv:tag:ct' (base64) gerado pelo web."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415

    iv_b64, tag_b64, ct_b64 = blob.split(":")
    iv = base64.b64decode(iv_b64)
    tag = base64.b64decode(tag_b64)
    ct = base64.b64decode(ct_b64)
    # `cryptography` espera ciphertext || tag concatenados
    plain = AESGCM(_key()).decrypt(iv, ct + tag, None)
    return plain.decode("utf-8")
