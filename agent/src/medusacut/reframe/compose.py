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
# O fundo borrado nao precisa de full-res: borrar em 1/5 (216x384) e reescalar custa
# ~25x menos que gblur em 1080x1920 — visual ~identico. (Era 41% do tempo total.)
_BLUR_W, _BLUR_H = TARGET_W // 5, TARGET_H // 5
_BLUR_SIGMA_SMALL = max(2, round(BLUR_SIGMA / 5))


def _squarify_cam_box(
    rect: tuple[float, float, float, float],
    media_w: int,
    media_h: int,
    *,
    max_aspect: float = 1.2,
) -> tuple[float, float, float, float]:
    """Da headroom vertical a uma caixa de facecam ACHATADA (larga/curta em PIXELS).

    Webcam (circular/quadrada) costuma vir como caixa curta porque coords normalizadas
    distorcem no frame 16:9 -> o crop corta queixo/topo da cabeca. Se a largura em px
    passa de `max_aspect`x a altura, aumenta a ALTURA em torno do centro (clampada)."""
    x0, y0, x1, y1 = rect
    pw = (x1 - x0) * media_w
    ph = (y1 - y0) * media_h
    if ph <= 0 or pw / ph <= max_aspect:
        return rect
    target_h = min(1.0, (pw / max_aspect) / media_h)  # nova altura normalizada
    cy = (y0 + y1) / 2.0
    ny0 = cy - target_h / 2.0
    ny1 = cy + target_h / 2.0
    # preserva a altura DESLOCANDO (nao so clampando) qdo bate numa borda — senao a
    # cam, que fica colada no topo, perde o queixo.
    if ny0 < 0.0:
        ny1 -= ny0
        ny0 = 0.0
    if ny1 > 1.0:
        ny0 -= ny1 - 1.0
        ny1 = 1.0
    return (x0, round(max(0.0, ny0), 4), x1, round(min(1.0, ny1), 4))


def _blurred_bg(src: str, out: str) -> str:
    """Filtro: preenche 9:16, borra num bg REDUZIDO e reescala (barato). `src`/`out`
    sao labels do filtergraph (ex.: 'bg' -> 'bgb')."""
    return (
        f"[{src}]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},scale={_BLUR_W}:{_BLUR_H},"
        f"gblur=sigma={_BLUR_SIGMA_SMALL},scale={TARGET_W}:{TARGET_H}[{out}]"
    )


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
    # headroom: evita cortar queixo/topo da cabeca quando a box vem achatada.
    rect = _squarify_cam_box(rect, int(media.width), int(media.height))

    os.makedirs(cache_dir, exist_ok=True)
    game_h = TARGET_H - facecam_h
    base = os.path.splitext(os.path.basename(out_path))[0]

    # UMA passada: a fonte e decodificada 1x e split em 3 (fundo borrado, facecam,
    # gameplay dinamico) — antes eram 2 passadas decodificando a fonte 60fps 2x +
    # um encode intermediario do painel.
    from medusacut.render.ffmpeg import dynamic_panel_segment

    plan = layouts.build_plan(
        media, candidate, dynamic=dynamic, facecam_corner=facecam_corner,
        facecam_box=rect, target_w=TARGET_W, target_h=game_h, cuts=cuts,
    )
    panel = dynamic_panel_segment(
        plan, src_label="gsrc", out_label="game",
        sendcmd_path=os.path.join(cache_dir, f"{base}.panel.sendcmd"),
    )

    cw = int(rect[2] * media.width) - int(rect[0] * media.width)
    ch = int(rect[3] * media.height) - int(rect[1] * media.height)
    cx = int(rect[0] * media.width)
    cy = int(rect[1] * media.height)
    filtergraph = (
        "[0:v]split=3[bg][cam][gsrc];"
        f"{_blurred_bg('bg', 'bgb')};"
        f"[cam]crop={cw}:{ch}:{cx}:{cy},"
        f"scale={TARGET_W}:{facecam_h}:force_original_aspect_ratio=decrease[camS];"
        f"[bgb][camS]overlay=x=(W-w)/2:y=({facecam_h}-h)/2[mid];"
        f"{panel};"
        f"[mid][game]overlay=x=0:y={facecam_h}[outv]"
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


def render_face_fullscreen(
    media: Media,
    candidate: Candidate,
    *,
    out_path: str,
    face_box: tuple[float, float, float, float] | None = None,
) -> str:
    """Rosto em TELA CHEIA 9:16 (reacao/camera fechada): recorta uma coluna 9:16 da
    altura toda, centrada no rosto, e escala. Sem split, sem blur — o rosto e o
    conteudo. `face_box` (x0,y0,x1,y1 normalizado) centra o crop; sem ela, centro."""
    iw, ih = int(media.width), int(media.height)
    crop_w = min(iw, int(round(ih * TARGET_W / TARGET_H)))  # 9:16 da altura cheia
    cx = 0.5 if not face_box else (face_box[0] + face_box[2]) / 2.0
    x = int(round(cx * iw - crop_w / 2))
    x = max(0, min(iw - crop_w, x))
    filtergraph = f"[0:v]crop={crop_w}:{ih}:{x}:0,scale={TARGET_W}:{TARGET_H}[outv]"
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


def render_blur_fit(media: Media, candidate: Candidate, *, out_path: str) -> str:
    """Gameplay inteiro (sem crop) encaixado sobre fundo desfocado."""
    filtergraph = (
        "[0:v]split=2[bg][fg];"
        f"{_blurred_bg('bg', 'bgb')};"
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
