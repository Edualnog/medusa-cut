"""Preprocess: extrai o audio do video via ffmpeg (mono 16 kHz WAV).

16 kHz mono e suficiente pro sinal de loudness e ja e o formato que o whisper
quer no Marco 2 — extraimos uma vez so.
"""

from __future__ import annotations

import os
import subprocess

from medusacut.types import Media


def extract_audio(media: Media, dest_dir: str) -> str:
    """Extrai o audio de `media` para `dest_dir/audio.wav` e devolve o caminho."""
    os.makedirs(dest_dir, exist_ok=True)
    out_path = os.path.join(dest_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", media.path,
        "-vn",            # sem video
        "-ac", "1",       # mono
        "-ar", "16000",   # 16 kHz
        "-f", "wav",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ao extrair audio de {media.path!r}:\n{proc.stderr.strip()}"
        )
    return out_path
