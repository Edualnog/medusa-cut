"""Fusao de sinais -> top-N candidatos com DURACAO AUTOMATICA.

Combina trilhas de score (ponderadas) numa trilha unica, escolhe os maiores picos
NAO-sobrepostos e, pra cada um, deixa a janela CRESCER enquanto a energia/acao se
sustenta (entre `min_len` e `max_len`). Assim o sistema decide o tamanho do corte
pelo conteudo — nada de fixar 30s e estragar um corte bom.

No Marco 1 entra so a trilha de audio; a interface ja aceita varias trilhas
(scene_change, chat_velocity) pra fusao premiar coincidencia depois.

Stdlib puro de proposito: da pra testar sem baixar video nem rodar ffmpeg.
"""

from __future__ import annotations

from medusacut.types import Candidate, ScoreTrack

# Limites e formato do corte (segundos). Pedido do dono: cortes longos 60s–3min.
MIN_LEN = 60.0
MAX_LEN = 180.0
# Fracao do pico ate onde a janela cresce ("ainda tem acao aqui?").
SUSTAIN_FRAC = 0.15
# Tolera vales curtos abaixo do limiar sem encerrar a janela (segundos).
GAP_TOL_SEC = 1.5
# Folga antes/depois pra dar contexto e nao cortar seco.
PAD_IN = 1.5
PAD_OUT = 0.7


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
    duration: float | None = None,
    weights: list[float] | None = None,
    min_score: float = 0.0,
    min_len: float = MIN_LEN,
    max_len: float = MAX_LEN,
) -> list[Candidate]:
    """Escolhe ate `max_clips` momentos; cada corte tem DURACAO AUTOMATICA.

    Guloso: pega o maior pico (score > `min_score`, i.e. acima da media), deixa a
    janela crescer pros lados enquanto o score se mantem acima de `SUSTAIN_FRAC`
    do pico, prende o tamanho em [`min_len`, `max_len`], descarta o que sobrepoe e
    repete. Devolve ordenado por score (desc).
    """
    if max_clips <= 0:
        return []
    if min_len <= 0 or max_len < min_len:
        raise ValueError("limites de duracao invalidos")

    times, scores = combine(tracks, weights)
    if not times:
        return []

    hop = tracks[0].hop
    if duration is None:
        duration = times[-1] + hop / 2.0

    order = sorted(range(len(times)), key=lambda i: scores[i], reverse=True)

    chosen: list[Candidate] = []
    for i in order:
        if len(chosen) >= max_clips or scores[i] <= min_score:
            break
        start, end = _auto_window(
            i, times, scores, hop, duration, min_len, max_len
        )
        if any(_overlaps(start, end, c.start, c.end) for c in chosen):
            continue
        chosen.append(Candidate(start=start, end=end, score=scores[i]))

    chosen.sort(key=lambda c: c.score, reverse=True)
    return chosen


def _auto_window(
    peak: int,
    times: list[float],
    scores: list[float],
    hop: float,
    duration: float,
    min_len: float,
    max_len: float,
) -> tuple[float, float]:
    """Cresce a janela ao redor de `peak` enquanto a acao se sustenta.

    Tolera vales curtos (ate `GAP_TOL_SEC`) abaixo do limiar pra nao encerrar o
    corte numa pausa breve — senao tudo colapsa no `min_len`.
    """
    thresh = max(0.0, scores[peak] * SUSTAIN_FRAC)
    gap_tol = max(1, int(round(GAP_TOL_SEC / hop)))

    left = peak
    gaps = 0
    j = peak
    while j - 1 >= 0:
        j -= 1
        if scores[j] >= thresh:
            left, gaps = j, 0
        else:
            gaps += 1
            if gaps > gap_tol:
                break

    right = peak
    gaps = 0
    j = peak
    while j + 1 < len(scores):
        j += 1
        if scores[j] >= thresh:
            right, gaps = j, 0
        else:
            gaps += 1
            if gaps > gap_tol:
                break

    start = times[left] - hop / 2.0 - PAD_IN
    end = times[right] + hop / 2.0 + PAD_OUT
    center = times[peak]

    # prende o tamanho em [min_len, max_len], crescendo/encolhendo em torno do pico
    length = end - start
    if length < min_len:
        start, end = center - min_len / 2.0, center + min_len / 2.0
    elif length > max_len:
        start, end = center - max_len / 2.0, center + max_len / 2.0

    # prende dentro de [0, duration] sem perder o tamanho-alvo
    target = min(max(end - start, min_len), max_len)
    if start < 0.0:
        start, end = 0.0, min(duration, target)
    if end > duration:
        end = duration
        start = max(0.0, end - target)
    return start, end


def _overlaps(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 < b1 and b0 < a1
