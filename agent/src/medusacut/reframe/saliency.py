"""Onde esta a ACAO em cada corte (pra o enquadramento 9:16 seguir o jogo).

Modelo de tracking (CV classica, roda em CPU no PC do usuario):
  1. **Optical flow** (Farneback) entre frames amostrados -> movimento COERENTE,
     ignora flicker/compressao melhor que diferenca de pixel crua. (Cai pra
     diferenca absoluta se o flow falhar.)
  2. **Vies de centro** (gaussiana): em FPS a acao fica perto da mira/centro, entao
     movimento na BORDA (muzzle flash, UI, explosao fora de foco) pesa menos.
  3. **Lock-on**: trava no foco dominante (mistura com o alvo anterior) e, em frame
     parado, SEGURA o enquadramento em vez de pular pro centro.
  4. Mascara a regiao do facecam (canto OU caixa detectada) pra o rosto nao puxar.

A suavizacao/keyframes ficam em `reframe/layouts.py`. OpenCV (cv2) importado DENTRO
da funcao — dep pesada.
"""

from __future__ import annotations

from medusacut.types import Candidate, Media

# Retangulos (normalizados x0,y0,x1,y1) tipicos de facecam por canto.
FACECAM_RECTS: dict[str, tuple[float, float, float, float]] = {
    "tl": (0.00, 0.00, 0.38, 0.42),
    "tr": (0.62, 0.00, 1.00, 0.42),
    "bl": (0.00, 0.58, 0.38, 1.00),
    "br": (0.62, 0.58, 1.00, 1.00),
}

# Parametros do tracking (calibrar vendo um corte real).
CENTER_SIGMA = 0.34   # largura do vies de centro (0..1); menor = mais preso ao centro
LOCK_BETA = 0.5       # quanto o alvo novo "puxa" vs. segurar o anterior (lock-on)
ENERGY_GATE = 1e-6    # abaixo disso e "parado" -> segura o enquadramento


def facecam_rect(corner: str | None) -> tuple[float, float, float, float] | None:
    """Retangulo normalizado do facecam pro canto pedido (ou None)."""
    if not corner:
        return None
    return FACECAM_RECTS.get(corner.lower())


def action_path(
    media: Media,
    candidate: Candidate,
    *,
    facecam_corner: str | None = None,
    facecam_box: tuple[float, float, float, float] | None = None,
    analysis_fps: float = 4.0,
    analysis_width: int = 320,
) -> list[tuple[float, float]]:
    """Devolve [(t_relativo_s, centro_x_normalizado_0a1), …] ao longo do corte.

    `facecam_box` (x0,y0,x1,y1 normalizado) tem prioridade sobre `facecam_corner`
    pra mascarar o rosto — usado quando o facecam foi auto-detectado.
    """
    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    cap = cv2.VideoCapture(media.path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV nao abriu o video: {media.path!r}")

    src_fps = media.fps or cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / analysis_fps)))
    start_f = int(candidate.start * src_fps)
    end_f = int(candidate.end * src_fps)

    rect = facecam_box or facecam_rect(facecam_corner)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    prev = None  # frame anterior em cinza (uint8)
    weight = None  # vies de centro (cacheado por largura)
    prev_cx = 0.5
    samples: list[tuple[float, float]] = []
    f = start_f
    while f < end_f:
        if (f - start_f) % step == 0:
            ok, frame = cap.read()
            if not ok:
                break
            h0, w0 = frame.shape[:2]
            small = cv2.resize(
                frame, (analysis_width, max(1, int(analysis_width * h0 / w0)))
            )
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                mag = _motion_magnitude(cv2, np, prev, gray)
                if rect is not None:
                    _mask_rect(mag, rect)
                col = mag.sum(axis=0)
                col = np.maximum(col - col.mean(), 0.0)  # gate: so acima da media
                if weight is None or weight.shape[0] != col.shape[0]:
                    weight = _center_weight(np, col.shape[0])
                prev_cx = _weighted_center(np, col, weight, prev_cx)
                samples.append(((f - start_f) / src_fps, prev_cx))
            prev = gray
        else:
            if not cap.grab():  # pula frame sem decodificar (rapido)
                break
        f += 1

    cap.release()
    return samples or [(0.0, 0.5)]


def _motion_magnitude(cv2, np, prev, gray):
    """Magnitude de movimento por pixel: optical flow (Farneback) com fallback
    pra diferenca absoluta se o flow falhar."""
    try:
        flow = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 2, 15, 3, 5, 1.2, 0)
        return np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
    except Exception:
        return np.abs(gray.astype(np.float32) - prev.astype(np.float32))


def _center_weight(np, n: int, sigma: float = CENTER_SIGMA):
    """Gaussiana 0..1 centrada no meio (vies pra acao do FPS perto da mira)."""
    if n <= 0:
        return np.ones(0, dtype=np.float32)
    pos = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return np.exp(-((pos - 0.5) ** 2) / (2.0 * sigma * sigma))


def _weighted_center(np, col, weight, prev_cx: float) -> float:
    """Centro horizontal (0..1) da energia ponderada pelo vies de centro, com
    lock-on: segura o anterior em frame parado e mistura no resto (anti ping-pong).
    """
    cw = col * weight
    total = float(cw.sum())
    if total <= ENERGY_GATE:
        return prev_cx  # parado -> segura o enquadramento (nao pula pro centro)
    pos = np.linspace(0.0, 1.0, col.shape[0], dtype=np.float32)
    cx_raw = float((pos * cw).sum() / total)
    return LOCK_BETA * cx_raw + (1.0 - LOCK_BETA) * prev_cx


def _mask_rect(arr, rect: tuple[float, float, float, float]) -> None:
    """Zera a regiao normalizada `rect` em `arr` (in-place)."""
    h, w = arr.shape[:2]
    x0 = int(rect[0] * w)
    y0 = int(rect[1] * h)
    x1 = int(rect[2] * w)
    y1 = int(rect[3] * h)
    arr[y0:y1, x0:x1] = 0.0
