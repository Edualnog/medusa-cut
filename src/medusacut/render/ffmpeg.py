"""Render final via ffmpeg: corta [start, end], aplica o filtro do layout e
escreve um mp4 vertical (H.264 + AAC).
"""

from __future__ import annotations

import os
import subprocess

from medusacut.types import Candidate, Media


def render_clip(
    media: Media,
    candidate: Candidate,
    video_filter: str,
    out_path: str,
) -> str:
    """Renderiza um corte e devolve `out_path`.

    `-ss` antes de `-i` faz seek rapido por keyframe; pra um tool pessoal o
    pequeno erro de inicio e aceitavel e o ganho de velocidade vale.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    duration = max(0.0, candidate.end - candidate.start)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{candidate.start:.3f}",
        "-i", media.path,
        "-t", f"{duration:.3f}",
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ao renderizar {out_path!r}:\n{proc.stderr.strip()}"
        )
    return out_path
