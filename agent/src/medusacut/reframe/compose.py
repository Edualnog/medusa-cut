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

from medusacut.reframe.saliency import facecam_rect
from medusacut.types import Candidate, Media

TARGET_W = 1080
TARGET_H = 1920
FACECAM_H = 640  # fallback da faixa de cima qdo nao da pra medir a proporcao do cam
# A altura do painel do facecam e ADAPTATIVA (casa com a proporcao do cam p/ encher a
# largura sem barras laterais), clampada nesta faixa p/ o gameplay seguir dominante.
FACECAM_H_MIN = 480
FACECAM_H_MAX = 760
# Encher o painel corta um pouco do cam. Acima deste corte vertical (fracao) preferimos
# ENCAIXAR centrado sobre o fundo borrado a cortar testa/queixo (cam alto/quadrado).
_MAX_CAM_VCROP = 0.20
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
    max_aspect: float = 1.7,
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


def _facecam_panel(
    cam_w_px: float, cam_h_px: float, *, default_h: int = FACECAM_H
) -> tuple[int, bool]:
    """Altura do painel do facecam + se ENCHE (cover) ou ENCAIXA (fit) o cam.

    O painel tem largura fixa `TARGET_W`. Escolhemos a altura que casa com a
    proporcao do cam (enche a largura sem barras laterais), clampada em
    `[FACECAM_H_MIN, FACECAM_H_MAX]` p/ o gameplay seguir dominante.

    Encher (cover) corta um pouco do cam. Se o corte vertical passar de
    `_MAX_CAM_VCROP` (cam alto/quadrado num painel mais baixo), devolve
    `fill=False` -> encaixa centrado sobre o fundo borrado (sem cortar o rosto)."""
    if cam_w_px <= 0 or cam_h_px <= 0:
        return default_h, True
    ar = cam_w_px / cam_h_px
    natural = TARGET_W / ar  # altura que enche a largura SEM cortar
    panel_h = int(round(min(FACECAM_H_MAX, max(FACECAM_H_MIN, natural))))
    panel_h -= panel_h % 2  # par (overlay/yuv420p): casa c/ game_h = TARGET_H - panel_h
    # cover so corta na vertical qdo o painel ficou mais BAIXO que o natural.
    vcrop = max(0.0, (natural - panel_h) / natural)
    return panel_h, vcrop <= _MAX_CAM_VCROP


def _blurred_bg(src: str, out: str) -> str:
    """Filtro: preenche 9:16, borra num bg REDUZIDO e reescala (barato). `src`/`out`
    sao labels do filtergraph (ex.: 'bg' -> 'bgb')."""
    return (
        f"[{src}]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},scale={_BLUR_W}:{_BLUR_H},"
        f"gblur=sigma={_BLUR_SIGMA_SMALL},scale={TARGET_W}:{TARGET_H}[{out}]"
    )


# LAYOUT A (padrao quando ha facecam): faixa do facecam no TERCO SUPERIOR,
# centralizada, com as laterais no fundo desfocado; gameplay preenchendo embaixo.
PANEL_H = TARGET_H // 3  # 640 = terco superior (par)


def render_facecam_layout(
    media: Media,
    candidate: Candidate,
    *,
    facecam_corner: str | None = None,
    out_path: str,
    cache_dir: str = ".",
    facecam_box: tuple[float, float, float, float] | None = None,
    **_ignored,
) -> str:
    """Layout A: facecam FIT-centralizada no terco superior (laterais com blur) +
    gameplay preenchendo o resto. Tudo sobre fundo desfocado (sem tarjas pretas).
    Uma passada de ffmpeg, SEM optical-flow (rapido e consistente).

    `facecam_box` (x0,y0,x1,y1 normalizado) e a regiao do facecam na fonte; sem ela,
    cai no preset do canto (`facecam_corner`)."""
    rect = facecam_box or facecam_rect(facecam_corner)
    if rect is None:
        raise ValueError(f"facecam_corner/box invalido p/ este layout: {facecam_corner!r}")
    # headroom: socorre box patologicamente achatada (evita cortar queixo/topo).
    rect = _squarify_cam_box(rect, int(media.width), int(media.height))
    cw = max(2, int(rect[2] * media.width) - int(rect[0] * media.width))
    ch = max(2, int(rect[3] * media.height) - int(rect[1] * media.height))
    cx = int(rect[0] * media.width)
    cy = int(rect[1] * media.height)

    panel_h = PANEL_H
    game_h = TARGET_H - panel_h
    os.makedirs(cache_dir, exist_ok=True)

    filtergraph = (
        # split: fundo borrado (canvas inteiro), facecam, gameplay
        "[0:v]split=3[bg][cam][game];"
        f"{_blurred_bg('bg', 'bgb')};"
        # facecam: recorta a caixa e ENCAIXA (fit) no terco superior, centralizado
        f"[cam]crop={cw}:{ch}:{cx}:{cy},"
        f"scale={TARGET_W}:{panel_h}:force_original_aspect_ratio=decrease[camS];"
        # gameplay: COBRE o painel de baixo (crop central) -> preenche sem barras
        f"[game]scale={TARGET_W}:{game_h}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{game_h}[gameS];"
        # compoe sobre o blur: cam centralizado no topo + game embaixo
        f"[bgb][camS]overlay=x=(W-w)/2:y=({panel_h}-h)/2[mid];"
        f"[mid][gameS]overlay=x=0:y={panel_h}[outv]"
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
