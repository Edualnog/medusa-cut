"""Onde esta a ACAO em cada corte (pra o enquadramento 9:16 seguir o jogo).

Mede movimento por coluna (diferenca entre frames amostrados, em baixa resolucao)
e devolve o centro horizontal da acao ao longo do tempo. Mascara a regiao do
facecam pra o rosto do streamer nao "puxar" o enquadramento.

OpenCV (cv2) importado DENTRO da funcao — dep pesada. Roda em CPU.
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
    analysis_fps: float = 4.0,
    analysis_width: int = 320,
) -> list[tuple[float, float]]:
    """Devolve [(t_relativo_s, centro_x_normalizado_0a1), …] ao longo do corte.

    `centro_x` e o centroide da energia de movimento por coluna. Sem movimento
    (ou corte minusculo) cai pra 0.5 (centro).
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

    rect = facecam_rect(facecam_corner)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    prev = None
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
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if prev is not None:
                diff = np.abs(gray - prev)
                if rect is not None:
                    _mask_rect(diff, rect)
                col = diff.sum(axis=0)
                col = np.maximum(col - col.mean(), 0.0)  # gate: so movimento acima da media
                total = float(col.sum())
                if total > 1e-6:
                    xs = np.arange(col.shape[0], dtype=np.float32)
                    cx = float((xs * col).sum() / total) / col.shape[0]
                    cx = 0.8 * cx + 0.2 * 0.5  # leve vies pro centro (menos tremido)
                else:
                    cx = 0.5
                samples.append(((f - start_f) / src_fps, cx))
            prev = gray
        else:
            if not cap.grab():  # pula frame sem decodificar (rapido)
                break
        f += 1

    cap.release()
    return samples or [(0.0, 0.5)]


def _mask_rect(arr, rect: tuple[float, float, float, float]) -> None:
    """Zera a regiao normalizada `rect` em `arr` (in-place)."""
    h, w = arr.shape[:2]
    x0 = int(rect[0] * w)
    y0 = int(rect[1] * h)
    x1 = int(rect[2] * w)
    y1 = int(rect[3] * h)
    arr[y0:y1, x0:x1] = 0.0
