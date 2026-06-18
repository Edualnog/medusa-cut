"""Sinal de MOVIMENTO visual: intensidade de acao por janela (z-score).

Complementa o audio na escolha do corte. Sozinho, o audio perde momento que e
VISUALMENTE intenso mas silencioso (clutch sem grito, explosao, kill rapido). Aqui
medimos a diferenca media entre frames amostrados (baixa resolucao, cinza) e
agregamos na MESMA grade de tempo do track de audio — pra `fusion.combine` poder
somar as duas trilhas.

DECODE via FFMPEG (um passe, em C): muito mais rapido que abrir frame-a-frame no
Python e funciona em qualquer codec (inclusive HEVC). O ffmpeg cospe frames cinza
160x90 em rawvideo num pipe; aqui so somamos as diferencas. numpy importado dentro;
`_zscore` e puro (testavel).
"""

from __future__ import annotations

import subprocess

from medusacut.types import Media, ScoreTrack

# resolucao de analise (pequena de proposito — energia de movimento, nao qualidade)
_W = 160
_H = 90


def analyze(
    media: Media,
    like: ScoreTrack,
    *,
    analysis_fps: float = 4.0,
) -> ScoreTrack:
    """Trilha de movimento alinhada a `like` (mesma grade/hop), z-score.

    `like` e tipicamente o track de audio — copiamos a grade de tempo dele pra as
    trilhas baterem na fusao. Le frames cinza do ffmpeg e mede a diferenca media.
    """
    import numpy as np  # noqa: PLC0415

    hop = like.hop
    n = len(like.times)
    if n == 0:
        return ScoreTrack(times=[], scores=[], hop=hop, name="motion")

    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error",
        "-i", media.path,
        "-vf", f"fps={analysis_fps},scale={_W}:{_H},format=gray",
        "-f", "rawvideo", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**7)
    frame_bytes = _W * _H

    acc = [0.0] * n
    cnt = [0] * n
    prev = None
    idx = 0
    try:
        assert proc.stdout is not None
        while True:
            raw = proc.stdout.read(frame_bytes)
            if len(raw) < frame_bytes:
                break
            cur = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            if prev is not None:
                wi = int((idx / analysis_fps) / hop)
                if 0 <= wi < n:
                    acc[wi] += float(np.abs(cur - prev).mean())
                    cnt[wi] += 1
            prev = cur
            idx += 1
    finally:
        if proc.stdout:
            proc.stdout.close()
        proc.wait()

    if proc.returncode not in (0, None) and idx == 0:
        raise RuntimeError(f"ffmpeg falhou ao ler frames (rc={proc.returncode})")

    raw_track = [acc[i] / cnt[i] if cnt[i] else 0.0 for i in range(n)]
    return ScoreTrack(times=list(like.times), scores=_zscore(raw_track), hop=hop, name="motion")


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
