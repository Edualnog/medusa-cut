"""Sinal de MOVIMENTO visual: intensidade de acao por janela (z-score).

Complementa o audio na escolha do corte (clutch/explosao silenciosos que o audio
perde). Agregado na MESMA grade de tempo do track de audio pra `fusion.combine`.

RAPIDO em video longo: decodifica so os KEYFRAMES (esparsos) via ffmpeg, em vez de
todo frame — o que tornava o passo lento (decode floor) em VOD de 1-2h. Em video
curto (poucos keyframes) cai pro decode completo a `analysis_fps`. numpy dentro;
`_zscore` puro (testavel).
"""

from __future__ import annotations

import subprocess

from medusacut.types import Media, ScoreTrack

_W = 160
_H = 90


def analyze(media: Media, like: ScoreTrack, *, analysis_fps: float = 4.0) -> ScoreTrack:
    """Trilha de movimento alinhada a `like`, z-score. Keyframes (rapido) ou full."""
    hop = like.hop
    n = len(like.times)
    if n == 0:
        return ScoreTrack(times=[], scores=[], hop=hop, name="motion")

    times = _keyframe_times(media.path)
    if len(times) >= 8:  # keyframes suficientes -> caminho RAPIDO
        raw = _keyframe_motion(media.path, times, hop, n)
    else:  # video curto/sem keyframes -> decode completo (ainda barato)
        raw = _full_motion(media.path, hop, n, analysis_fps)
    return ScoreTrack(times=list(like.times), scores=_zscore(raw), hop=hop, name="motion")


def _keyframe_times(path: str) -> list[float]:
    """Tempos (s) dos keyframes — via PACOTES (sem decodificar), rapido."""
    pr = subprocess.run(
        ["ffprobe", "-loglevel", "error", "-select_streams", "v:0",
         "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    out: list[float] = []
    for line in pr.stdout.splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and "K" in parts[1]:
            try:
                out.append(float(parts[0]))
            except ValueError:
                pass
    return sorted(out)


def _keyframe_motion(path: str, times: list[float], hop: float, n: int) -> list[float]:
    """Diferenca entre keyframes consecutivos (decodifica so eles)."""
    import numpy as np  # noqa: PLC0415

    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error", "-skip_frame", "nokey",
        "-i", path, "-vf", f"scale={_W}:{_H},format=gray",
        "-fps_mode", "passthrough", "-f", "rawvideo", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**7)
    fb = _W * _H
    frames: list = []
    try:
        assert proc.stdout is not None
        while True:
            raw = proc.stdout.read(fb)
            if len(raw) < fb:
                break
            frames.append(np.frombuffer(raw, dtype=np.uint8).astype(np.float32))
    finally:
        if proc.stdout:
            proc.stdout.close()
        proc.wait()

    acc = [0.0] * n
    cnt = [0] * n
    m = min(len(frames), len(times))
    for i in range(1, m):
        wi = int(times[i] / hop)
        if 0 <= wi < n:
            acc[wi] += float(np.abs(frames[i] - frames[i - 1]).mean())
            cnt[wi] += 1
    return [acc[i] / cnt[i] if cnt[i] else 0.0 for i in range(n)]


def _full_motion(path: str, hop: float, n: int, analysis_fps: float) -> list[float]:
    """Decode completo a `analysis_fps` (fallback p/ video curto)."""
    import numpy as np  # noqa: PLC0415

    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error", "-i", path,
        "-vf", f"fps={analysis_fps},scale={_W}:{_H},format=gray",
        "-f", "rawvideo", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**7)
    fb = _W * _H
    acc = [0.0] * n
    cnt = [0] * n
    prev = None
    idx = 0
    try:
        assert proc.stdout is not None
        while True:
            raw = proc.stdout.read(fb)
            if len(raw) < fb:
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
    return [acc[i] / cnt[i] if cnt[i] else 0.0 for i in range(n)]


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
