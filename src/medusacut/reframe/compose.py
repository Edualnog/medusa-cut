"""Composicoes 9:16 com varios elementos (ffmpeg overlay).

- `facecam_top_gameplay_bottom`: rosto do streamer em cima, gameplay (reframe
  dinamico) embaixo, tudo sobre um FUNDO DESFOCADO (sem tarjas pretas).
- `gameplay_blur`: gameplay inteiro (sem crop) encaixado sobre fundo desfocado —
  ajusta a proporcao sem perder nada da tela.

O panning dinamico (sendcmd) so funciona bem isolado, entao o layout com facecam
e feito em DOIS PASSES: (1) renderiza o painel de gameplay; (2) compoe.
"""

from __future__ import annotations

import os
import subprocess

from medusacut.reframe import layouts
from medusacut.reframe.saliency import facecam_rect
from medusacut.types import Candidate, Media

TARGET_W = 1080
TARGET_H = 1920
FACECAM_H = 640  # faixa de cima (rosto); resto e gameplay
BLUR_SIGMA = 24


def render_facecam_layout(
    media: Media,
    candidate: Candidate,
    *,
    facecam_corner: str,
    out_path: str,
    cache_dir: str,
    dynamic: bool = True,
    facecam_box: tuple[float, float, float, float] | None = None,
    facecam_h: int = FACECAM_H,
    cuts: list[float] | None = None,
) -> str:
    """Rosto em cima + gameplay dinamico embaixo + blur.

    A caixa do facecam vem de `facecam_box` (x0,y0,x1,y1 normalizados) se dado,
    senao do preset do `facecam_corner`. `facecam_h` controla a altura do painel."""
    rect = facecam_box or facecam_rect(facecam_corner)
    if rect is None:
        raise ValueError(f"facecam_corner/box invalido p/ este layout: {facecam_corner!r}")

    os.makedirs(cache_dir, exist_ok=True)
    game_h = TARGET_H - facecam_h

    # Pass 1: painel de gameplay (reframe dinamico) em 1080 x game_h.
    base = os.path.splitext(os.path.basename(out_path))[0]
    panel = os.path.join(cache_dir, f"{base}.panel.mp4")
    plan = layouts.build_plan(
        media, candidate, dynamic=dynamic, facecam_corner=facecam_corner,
        target_w=TARGET_W, target_h=game_h, cuts=cuts,
    )
    from medusacut.render import ffmpeg as render

    render.render_clip(media, candidate, plan, panel, cache_dir=cache_dir)

    # Pass 2: compoe fundo borrado + facecam (cima) + painel (baixo).
    cw = int(rect[2] * media.width) - int(rect[0] * media.width)
    ch = int(rect[3] * media.height) - int(rect[1] * media.height)
    cx = int(rect[0] * media.width)
    cy = int(rect[1] * media.height)
    filtergraph = (
        "[0:v]split=2[bg][cam];"
        f"[bg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},gblur=sigma={BLUR_SIGMA}[bgb];"
        f"[cam]crop={cw}:{ch}:{cx}:{cy},"
        f"scale={TARGET_W}:{facecam_h}:force_original_aspect_ratio=decrease[camS];"
        f"[bgb][camS]overlay=x=(W-w)/2:y=({facecam_h}-h)/2[mid];"
        f"[1:v]scale={TARGET_W}:{game_h}[game];"
        f"[mid][game]overlay=x=0:y={facecam_h}[outv]"
    )
    dur = max(0.0, candidate.end - candidate.start)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{candidate.start:.3f}", "-t", f"{dur:.3f}", "-i", media.path,
        "-i", panel,
        "-filter_complex", filtergraph,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", out_path,
    ]
    _run(cmd, out_path)
    return out_path


def render_blur_fit(media: Media, candidate: Candidate, *, out_path: str) -> str:
    """Gameplay inteiro (sem crop) encaixado sobre fundo desfocado."""
    filtergraph = (
        "[0:v]split=2[bg][fg];"
        f"[bg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},gblur=sigma={BLUR_SIGMA}[bgb];"
        f"[fg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease[fgs];"
        "[bgb][fgs]overlay=x=(W-w)/2:y=(H-h)/2[outv]"
    )
    dur = max(0.0, candidate.end - candidate.start)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{candidate.start:.3f}", "-t", f"{dur:.3f}", "-i", media.path,
        "-filter_complex", filtergraph,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", out_path,
    ]
    _run(cmd, out_path)
    return out_path


def _run(cmd: list[str], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ao compor {out_path!r}:\n{proc.stderr.strip()}"
        )
