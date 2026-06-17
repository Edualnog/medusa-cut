"""Render final via ffmpeg: corta [start, end], aplica o plano de enquadramento
(estatico ou com panning dinamico) e escreve um mp4 vertical 9:16 (H.264 + AAC).
"""

from __future__ import annotations

import os
import subprocess

from medusacut.reframe.layouts import ReframePlan
from medusacut.types import Candidate, Media


def render_clip(
    media: Media,
    candidate: Candidate,
    plan: ReframePlan,
    out_path: str,
    *,
    cache_dir: str | None = None,
) -> str:
    """Renderiza um corte conforme `plan` e devolve `out_path`.

    `-ss` antes de `-i` faz seek rapido; o stream filtrado comeca em t=0, entao os
    keyframes do plano (t relativo ao corte) ficam alinhados com o `sendcmd`.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    duration = max(0.0, candidate.end - candidate.start)
    video_filter = _build_filter(plan, out_path, cache_dir)

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


def _build_filter(plan: ReframePlan, out_path: str, cache_dir: str | None) -> str:
    """Monta o -vf: crop (+ sendcmd se dinamico) e scale pro 9:16 final."""
    x0 = plan.keyframes[0][1]
    crop = f"crop={plan.crop_w}:{plan.crop_h}:{x0:.1f}:0"
    scale = f"scale={plan.target_w}:{plan.target_h}"

    if not plan.is_dynamic:
        return f"{crop},{scale}"

    cmd_path = _write_sendcmd(plan, out_path, cache_dir)
    # sendcmd move o 'x' do crop ao longo do tempo; aspas simples no caminho.
    return f"sendcmd=f='{cmd_path}',{crop},{scale}"


def _write_sendcmd(plan: ReframePlan, out_path: str, cache_dir: str | None) -> str:
    """Escreve o script do sendcmd (um comando 'crop x <px>' por keyframe)."""
    base = os.path.splitext(os.path.basename(out_path))[0]
    target_dir = cache_dir or os.path.dirname(out_path) or "."
    os.makedirs(target_dir, exist_ok=True)
    cmd_path = os.path.join(target_dir, f"{base}.sendcmd")
    lines = [f"{t:.3f} crop x {x:.1f};" for t, x in plan.keyframes]
    with open(cmd_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return cmd_path
