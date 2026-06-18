"""Sinal de MOVIMENTO visual: intensidade de acao por janela (z-score).

Complementa o audio na escolha do corte. Sozinho, o audio perde momento que e
VISUALMENTE intenso mas silencioso (clutch sem grito, explosao, kill rapido). Aqui
medimos a diferenca media entre frames amostrados (baixa resolucao, cinza) e
agregamos na MESMA grade de tempo do track de audio — pra `fusion.combine` poder
somar as duas trilhas.

cv2/numpy importados dentro da funcao (deps pesadas). `_zscore` e puro (testavel).
"""

from __future__ import annotations

from medusacut.types import Media, ScoreTrack


def analyze(
    media: Media,
    like: ScoreTrack,
    *,
    analysis_fps: float = 4.0,
    width: int = 320,
) -> ScoreTrack:
    """Trilha de movimento alinhada a `like` (mesma grade/hop), z-score.

    `like` e tipicamente o track de audio — copiamos sua grade de tempo pra as
    trilhas baterem na fusao.
    """
    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    hop = like.hop
    n = len(like.times)
    if n == 0:
        return ScoreTrack(times=[], scores=[], hop=hop, name="motion")

    cap = cv2.VideoCapture(media.path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV nao abriu o video: {media.path!r}")

    src_fps = media.fps or cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / analysis_fps)))

    acc = [0.0] * n
    cnt = [0] * n
    prev = None
    f = 0
    try:
        while True:
            if f % step == 0:
                ok, frame = cap.read()
                if not ok:
                    break
                h0, w0 = frame.shape[:2]
                small = cv2.resize(frame, (width, max(1, int(width * h0 / w0))))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
                if prev is not None:
                    wi = int((f / src_fps) / hop)
                    if 0 <= wi < n:
                        acc[wi] += float(np.abs(gray - prev).mean())
                        cnt[wi] += 1
                prev = gray
            else:
                if not cap.grab():
                    break
            f += 1
    finally:
        cap.release()

    raw = [acc[i] / cnt[i] if cnt[i] else 0.0 for i in range(n)]
    return ScoreTrack(times=list(like.times), scores=_zscore(raw), hop=hop, name="motion")


def _zscore(raw: list[float]) -> list[float]:
    """Z-score puro (stdlib) — deixa a trilha comparavel com a de audio."""
    n = len(raw)
    if n == 0:
        return []
    mean = sum(raw) / n
    std = (sum((x - mean) ** 2 for x in raw) / n) ** 0.5
    if std < 1e-9:
        return [0.0] * n
    return [(x - mean) / std for x in raw]
