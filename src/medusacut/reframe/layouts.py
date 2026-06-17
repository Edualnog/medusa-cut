"""Enquadramento 9:16: do video fonte pro frame vertical do TikTok (1080x1920).

- `gameplay_only`: crop central estatico (rapido, sem analise).
- `dynamic_gameplay`: o recorte SEGUE A ACAO ao longo do corte (caminho suavizado
  vindo de signals/saliency), escondendo o facecam. Foca no jogo, nao no streamer.

A matematica de crop/suavizacao e stdlib puro (testavel sem video); a analise de
movimento (OpenCV) mora em `reframe/saliency.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from medusacut.types import Candidate, Media

TARGET_W = 1080
TARGET_H = 1920  # 9:16

# Suavizacao do caminho (EMA) e quanto a janela pode andar entre amostras (px/s)
# sao calibrados na pratica, vendo um corte real.
SMOOTH_ALPHA = 0.25


@dataclass
class ReframePlan:
    """Como recortar um corte: dimensoes e o caminho do x ao longo do tempo."""

    crop_w: int
    crop_h: int
    target_w: int
    target_h: int
    keyframes: list[tuple[float, float]]  # [(t_relativo_s, x_pixels), …]; len>=1
    name: str = "gameplay_only"

    @property
    def is_dynamic(self) -> bool:
        return len(self.keyframes) > 1


def crop_dims(width: int, height: int, target_w: int = TARGET_W, target_h: int = TARGET_H) -> tuple[int, int]:
    """Maior retangulo de aspecto target_w:target_h dentro de (width x height)."""
    target_ar = target_w / target_h
    source_ar = width / height
    if source_ar > target_ar:  # fonte mais larga: limita pela altura
        cw, ch = int(round(height * target_ar)), height
    else:  # fonte mais alta/estreita: limita pela largura
        cw, ch = width, int(round(width / target_ar))
    cw -= cw % 2  # H.264 quer dimensoes pares
    ch -= ch % 2
    return cw, ch


def smooth_centers(centers: list[float], alpha: float = SMOOTH_ALPHA) -> list[float]:
    """EMA simples pra tirar o tremido do caminho de enquadramento."""
    out: list[float] = []
    acc = centers[0] if centers else 0.5
    for c in centers:
        acc = alpha * c + (1.0 - alpha) * acc
        out.append(acc)
    return out


def centers_to_keyframes(
    samples: list[tuple[float, float]],
    width: int,
    crop_w: int,
    alpha: float = SMOOTH_ALPHA,
    cuts: list[float] | None = None,
) -> list[tuple[float, float]]:
    """Converte centros normalizados (0..1) em x de crop em pixels, suavizado e
    preso pra a janela 9:16 nao sair do frame.

    `cuts` sao tempos (relativos ao corte) de troca de cena: a suavizacao REINICIA
    em cada um, entao o enquadramento salta pra a nova cena em vez de varrer por
    cima do corte."""
    if not samples:
        return [(0.0, float((width - crop_w) // 2))]
    cut_list = sorted(cuts or [])
    max_x = max(0, width - crop_w)
    keyframes: list[tuple[float, float]] = []

    def flush(seg: list[tuple[float, float]]) -> None:
        smoothed = smooth_centers([c for _, c in seg], alpha)
        for (t, _), cs in zip(seg, smoothed):
            x = min(max(cs * width - crop_w / 2.0, 0.0), float(max_x))
            keyframes.append((t, round(x, 1)))

    seg: list[tuple[float, float]] = []
    ci = 0
    for t, c in samples:
        while ci < len(cut_list) and t >= cut_list[ci]:
            if seg:
                flush(seg)
                seg = []
            ci += 1
        seg.append((t, c))
    if seg:
        flush(seg)
    return keyframes


def build_plan(
    media: Media,
    candidate: Candidate,
    *,
    dynamic: bool = True,
    facecam_corner: str | None = None,
    target_w: int = TARGET_W,
    target_h: int = TARGET_H,
    cuts: list[float] | None = None,
) -> ReframePlan:
    """Monta o plano de recorte de um corte (dinamico por padrao).

    `cuts` sao tempos absolutos de troca de cena no video; o que cair dentro do
    corte faz o enquadramento saltar (ver centers_to_keyframes)."""
    cw, ch = crop_dims(media.width, media.height, target_w, target_h)
    center_x = float((media.width - cw) // 2)

    if not dynamic:
        return ReframePlan(cw, ch, target_w, target_h, [(0.0, center_x)], "gameplay_only")

    from medusacut.reframe import saliency

    samples = saliency.action_path(media, candidate, facecam_corner=facecam_corner)
    rel_cuts = [c - candidate.start for c in (cuts or []) if candidate.start < c < candidate.end]
    keyframes = centers_to_keyframes(samples, media.width, cw, cuts=rel_cuts)
    if keyframes and keyframes[0][0] > 0.0:
        keyframes.insert(0, (0.0, keyframes[0][1]))  # garante comando em t=0
    return ReframePlan(cw, ch, target_w, target_h, keyframes, "dynamic_gameplay")
