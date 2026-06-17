"""Sinal de energia de audio: loudness por janela, normalizado em z-score.

A selecao de momento e por fusao de sinais (nao por transcricao). Este e o
primeiro sinal: picos relativos de loudness costumam marcar acao/reacao em
gameplay. A normalizacao em z-score deixa o score comparavel entre videos.
"""

from __future__ import annotations

import wave

from medusacut.types import ScoreTrack


def analyze(wav_path: str, hop: float = 0.5) -> ScoreTrack:
    """Le um WAV mono PCM16 e devolve uma ScoreTrack de loudness (z-score).

    Janelas nao-sobrepostas de `hop` segundos; score = z-score do loudness (dBFS)
    da janela. `numpy` importado aqui dentro (dep pesada).
    """
    import numpy as np  # noqa: PLC0415

    with wave.open(wav_path, "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError(
                f"esperava PCM 16-bit, veio sampwidth={wf.getsampwidth()} "
                f"(use o preprocess.extract_audio)"
            )
        sr = wf.getframerate()
        channels = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if channels > 1:  # defensivo; o preprocess ja entrega mono
        samples = samples.reshape(-1, channels).mean(axis=1)
    samples /= 32768.0  # normaliza pra [-1, 1)

    win = max(1, int(round(sr * hop)))
    n_windows = len(samples) // win
    if n_windows == 0:
        raise ValueError("audio curto demais para a janela escolhida")

    framed = samples[: n_windows * win].reshape(n_windows, win)
    rms = np.sqrt(np.mean(framed**2, axis=1))
    loudness = 20.0 * np.log10(rms + 1e-9)  # dBFS, evita log(0)

    std = loudness.std()
    z = (loudness - loudness.mean()) / std if std > 1e-9 else loudness * 0.0

    times = (np.arange(n_windows) + 0.5) * hop
    return ScoreTrack(
        times=times.tolist(),
        scores=z.tolist(),
        hop=hop,
        name="audio_energy",
    )
