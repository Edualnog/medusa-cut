"""Reframe CIENTE DE CENA: escolhe o layout 9:16 por TRECHO, nao um fixo pro clipe.

Video editado troca de composicao cena a cena (gameplay+cam / reacao fullscreen /
gameplay puro). Aqui a gente:
  1. parte o clipe nas trocas de cena (`scene.detect_cuts`);
  2. classifica cada cena (`composition.classify_segment` — VLM, fallback YuNet);
  3. junta cenas vizinhas do MESMO modo (menos cortes de render/concat);
  4. renderiza cada run com o layout certo;
  5. concatena num clipe so.

Assim a reacao fullscreen vira rosto em tela cheia (em vez de parede no topo) e o
gameplay puro vira crop dinamico (em vez de split com box errada).

`_scene_bounds` e `_merge_runs` sao puras (testaveis). ffmpeg/cv2/LLM ficam nas
funcoes de render.
"""

from __future__ import annotations

import os
from statistics import median

from medusacut.reframe import composition as C
from medusacut.types import Candidate, Media

# Cena curta demais nao vira segmento proprio — funde na anterior (evita micro-cortes
# e troca de layout epileptica).
MIN_SCENE = 2.5
# Teto de cenas classificadas por clipe (controla custo de VLM e tempo). Acima disso,
# amostra menos (junta cenas).
MAX_SCENES = 12


def render_scene_aware(
    media: Media,
    candidate: Candidate,
    *,
    out_path: str,
    cache_dir: str,
    cuts: list[float] | None = None,
    facecam_corner: str | None = None,
    facecam_h: int = 640,
    use_vlm: bool = True,
) -> str:
    """Renderiza o clipe escolhendo o layout por cena. Devolve `out_path`."""
    os.makedirs(cache_dir, exist_ok=True)
    bounds = _scene_bounds(candidate.start, candidate.end, cuts, min_scene=MIN_SCENE)
    bounds = _cap_scenes(bounds, MAX_SCENES)

    # classifica as cenas EM PARALELO (VLM e rede; cenas sao independentes) e junta
    # vizinhas do mesmo modo. Cada cena escreve keyframes num subdir proprio (evita
    # colisao de nomes entre threads).
    from concurrent.futures import ThreadPoolExecutor

    def _classify(item):
        i, (a, b) = item
        sub = os.path.join(cache_dir, f"cls{i:02d}")
        return (a, b, C.classify_segment(media.path, a, b, use_vlm=use_vlm, cache_dir=sub))

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(bounds)))) as ex:
        classified = list(ex.map(_classify, enumerate(bounds)))
    runs = _merge_runs(classified)

    # render por run
    base = os.path.splitext(os.path.basename(out_path))[0]
    parts: list[str] = []
    for i, (a, b, comp) in enumerate(runs):
        part = os.path.join(cache_dir, f"{base}.seg{i:02d}.mp4")
        _render_run(media, a, b, comp, part, cache_dir, facecam_corner, facecam_h, cuts)
        parts.append(part)

    if len(parts) == 1:
        os.replace(parts[0], out_path)
    else:
        _concat(parts, out_path, cache_dir)
    return out_path


def _render_run(
    media: Media,
    a: float,
    b: float,
    comp: C.SceneComposition,
    out_path: str,
    cache_dir: str,
    facecam_corner: str | None,
    facecam_h: int,
    cuts: list[float] | None,
) -> None:
    """Despacha 1 run pro render do seu modo."""
    from medusacut.reframe import compose, layouts
    from medusacut.render import ffmpeg as render

    cand = Candidate(a, b, 0.0)
    seg_cuts = [c for c in (cuts or []) if a < c < b]

    if comp.mode == C.FULLSCREEN_FACE:
        compose.render_face_fullscreen(media, cand, out_path=out_path, face_box=comp.face_box)
    elif comp.mode == C.GAMEPLAY_CAM and comp.cam_box is not None:
        compose.render_facecam_layout(
            media, cand, facecam_corner=facecam_corner, out_path=out_path,
            cache_dir=cache_dir, dynamic=True, facecam_box=comp.cam_box,
            facecam_h=facecam_h, cuts=seg_cuts,
        )
    else:  # GAMEPLAY_ONLY (ou cam sem box) -> crop dinamico tela cheia
        plan = layouts.build_plan(media, cand, dynamic=True, facecam_corner=None, cuts=seg_cuts)
        render.render_clip(media, cand, plan, out_path, cache_dir=cache_dir)


# ------------------------------------------------------------------ cenas (puras)


def _scene_bounds(
    start: float, end: float, cuts: list[float] | None, *, min_scene: float
) -> list[tuple[float, float]]:
    """Segmenta [start,end] nas trocas de cena internas; funde cenas < min_scene."""
    inner = sorted(c for c in (cuts or []) if start < c < end)
    points = [start, *inner, end]
    segs: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:]):
        if b <= a:
            continue
        if segs and (b - a) < min_scene:
            segs[-1] = (segs[-1][0], b)  # funde na anterior
        else:
            segs.append((a, b))
    # se a primeira ficou curta, funde na seguinte
    if len(segs) >= 2 and (segs[0][1] - segs[0][0]) < min_scene:
        segs[1] = (segs[0][0], segs[1][1])
        segs.pop(0)
    return segs or [(start, end)]


def _cap_scenes(bounds: list[tuple[float, float]], cap: int) -> list[tuple[float, float]]:
    """Limita o nº de cenas fundindo as mais curtas com a vizinha (controla custo)."""
    segs = list(bounds)
    while len(segs) > cap:
        # acha a cena mais curta e funde com a vizinha mais curta
        i = min(range(len(segs)), key=lambda k: segs[k][1] - segs[k][0])
        j = i - 1 if i > 0 and (i == len(segs) - 1 or
                                 (segs[i - 1][1] - segs[i - 1][0]) <=
                                 (segs[i + 1][1] - segs[i + 1][0])) else i + 1
        lo, hi = (j, i) if j < i else (i, j)
        segs[lo] = (segs[lo][0], segs[hi][1])
        segs.pop(hi)
    return segs


def _merge_runs(classified: list) -> list:
    """Funde cenas CONSECUTIVAS do mesmo modo num run. Caixas viram a mediana.

    Entrada: [(a,b,SceneComposition)]. Saida: [(a,b,SceneComposition)] (runs).
    """
    runs: list = []
    for a, b, comp in classified:
        if runs and runs[-1][2].mode == comp.mode:
            pa, _pb, pc = runs[-1]
            runs[-1] = (pa, b, _merge_comp(pc, comp))
        else:
            runs.append((a, b, comp))
    return runs


def _merge_comp(c1: C.SceneComposition, c2: C.SceneComposition) -> C.SceneComposition:
    """Funde duas comps do mesmo modo: caixa = mediana, confianca = media."""
    cam = _median_box(c1.cam_box, c2.cam_box)
    face = _median_box(c1.face_box, c2.face_box)
    return C.SceneComposition(
        c1.mode, cam_box=cam, face_box=face,
        confidence=(c1.confidence + c2.confidence) / 2.0,
        source=c1.source,
    )


def _median_box(b1, b2):
    if b1 and b2:
        return tuple(round(median([b1[i], b2[i]]), 4) for i in range(4))
    return b1 or b2


def _concat(parts: list[str], out_path: str, cache_dir: str) -> None:
    """Concatena segmentos (mesmos codecs/params) via concat demuxer, sem re-encode."""
    import subprocess

    listf = os.path.join(cache_dir, os.path.basename(out_path) + ".concat.txt")
    with open(listf, "w", encoding="utf-8") as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
        "-c", "copy", "-movflags", "+faststart", out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # fallback: re-encode (timestamps/params destoaram)
        cmd2 = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", out_path,
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        if proc2.returncode != 0:
            raise RuntimeError(f"concat falhou:\n{proc.stderr.strip()}\n{proc2.stderr.strip()}")
