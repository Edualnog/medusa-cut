"""Fusao de sinais -> top-N candidatos.

Combina trilhas de score (ponderadas) numa trilha unica e escolhe os melhores
momentos NAO-sobrepostos, cada um virando uma janela de `clip_len` segundos.

No Marco 1 entra so a trilha de audio; a interface ja aceita varias trilhas
(scene_change, chat_velocity) pra fusao premiar coincidencia depois.

Stdlib puro de proposito: da pra testar sem baixar video nem rodar ffmpeg.
"""

from __future__ import annotations

from medusacut.types import Candidate, ScoreTrack


def combine(
    tracks: list[ScoreTrack],
    weights: list[float] | None = None,
) -> tuple[list[float], list[float]]:
    """Funde varias trilhas numa so (soma ponderada), na grade da 1a trilha.

    Exige que as trilhas compartilhem a mesma grade de tempo (mesmo `times`).
    Devolve `(times, scores)`.
    """
    if not tracks:
        raise ValueError("nenhuma trilha para fundir")

    base = tracks[0]
    if weights is None:
        weights = [1.0] * len(tracks)
    if len(weights) != len(tracks):
        raise ValueError("weights e tracks com tamanhos diferentes")

    times = list(base.times)
    scores = [0.0] * len(times)
    for track, w in zip(tracks, weights):
        if len(track.times) != len(times):
            raise ValueError(
                "trilhas com grades de tempo diferentes; alinhe antes de fundir "
                f"({track.name}: {len(track.times)} vs base: {len(times)})"
            )
        for i, s in enumerate(track.scores):
            scores[i] += w * s
    return times, scores


def select_candidates(
    tracks: list[ScoreTrack],
    *,
    max_clips: int,
    clip_len: float,
    duration: float | None = None,
    weights: list[float] | None = None,
    min_score: float = 0.0,
) -> list[Candidate]:
    """Escolhe ate `max_clips` janelas de `clip_len` s nos maiores picos.

    Guloso: pega o maior score, fixa uma janela centrada nele, descarta o que
    sobrepoe, repete. So considera picos com score > `min_score` — por padrao 0,
    ou seja, acima da media (z-score). Assim um video calmo rende MENOS cortes em
    vez de encher `max_clips` com trechos sem energia. Devolve ordenado por score.
    """
    if max_clips <= 0:
        return []
    if clip_len <= 0:
        raise ValueError("clip_len precisa ser > 0")

    times, scores = combine(tracks, weights)
    if not times:
        return []

    hop = tracks[0].hop
    if duration is None:
        duration = times[-1] + hop / 2.0

    half = clip_len / 2.0
    order = sorted(range(len(times)), key=lambda i: scores[i], reverse=True)

    chosen: list[Candidate] = []
    for i in order:
        if len(chosen) >= max_clips or scores[i] <= min_score:
            break
        start, end = _window(times[i], half, clip_len, duration)
        if any(_overlaps(start, end, c.start, c.end) for c in chosen):
            continue
        chosen.append(Candidate(start=start, end=end, score=scores[i]))

    chosen.sort(key=lambda c: c.score, reverse=True)
    return chosen


def _window(center: float, half: float, clip_len: float, duration: float) -> tuple[float, float]:
    """Janela de `clip_len` centrada em `center`, presa dentro de [0, duration]."""
    if clip_len >= duration:
        return 0.0, duration
    start = center - half
    if start < 0.0:
        start = 0.0
    end = start + clip_len
    if end > duration:
        end = duration
        start = end - clip_len
    return start, end


def _overlaps(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 < b1 and b0 < a1
