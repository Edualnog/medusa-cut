"""Testes da fusao. Stdlib puro: nao baixa video nem chama ffmpeg/numpy."""

from __future__ import annotations

from medusacut.signals.fusion import combine, select_candidates
from medusacut.types import ScoreTrack


def _track(scores: list[float], hop: float = 1.0, name: str = "t") -> ScoreTrack:
    times = [(i + 0.5) * hop for i in range(len(scores))]
    return ScoreTrack(times=times, scores=scores, hop=hop, name=name)


def test_picks_top_n_peaks_non_overlapping():
    # picos em t~10, t~50, t~90; resto baixo.
    scores = [0.0] * 100
    scores[10] = 5.0
    scores[50] = 4.0
    scores[90] = 3.0
    track = _track(scores)

    cands = select_candidates([track], max_clips=3, clip_len=20.0, duration=100.0)

    assert len(cands) == 3
    # ordenados por score desc
    assert [round(c.score) for c in cands] == [5, 4, 3]
    # nenhuma sobreposicao entre janelas
    ordered = sorted(cands, key=lambda c: c.start)
    for a, b in zip(ordered, ordered[1:]):
        assert a.end <= b.start
    # todas tem a duracao pedida
    for c in cands:
        assert abs(c.duration - 20.0) < 1e-6


def test_overlapping_peaks_collapse_to_one():
    # dois picos a 5 s de distancia (dentro de uma janela de 20 s) + um longe.
    scores = [0.0] * 100
    scores[10] = 5.0
    scores[15] = 4.0  # deve ser descartado: sobrepoe o pico de t=10
    scores[80] = 3.0
    track = _track(scores)

    cands = select_candidates([track], max_clips=3, clip_len=20.0, duration=100.0)

    assert len(cands) == 2
    starts = sorted(round(c.start) for c in cands)
    # janela do pico forte (centro ~10 -> [0,20]) e a do pico distante (~80 -> [70,90])
    assert starts == [0, 70]


def test_clip_len_larger_than_video_returns_single_full_window():
    track = _track([1.0, 2.0, 3.0], hop=1.0)  # duracao ~3 s
    cands = select_candidates([track], max_clips=5, clip_len=30.0, duration=3.0)
    assert len(cands) == 1
    assert cands[0].start == 0.0
    assert cands[0].end == 3.0


def test_combine_weighted_sum_requires_aligned_grids():
    a = _track([1.0, 0.0, 0.0], name="audio")
    b = _track([0.0, 0.0, 2.0], name="scene")
    times, scores = combine([a, b], weights=[1.0, 0.5])
    assert times == a.times
    assert scores == [1.0, 0.0, 1.0]


def test_max_clips_zero_returns_empty():
    assert select_candidates([_track([1.0, 2.0])], max_clips=0, clip_len=1.0) == []
