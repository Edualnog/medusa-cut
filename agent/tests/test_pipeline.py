"""Testes de logica pura do pipeline (sem ffmpeg/LLM)."""

from __future__ import annotations

from pytest import approx

import os

from medusacut.pipeline import (
    SIGNAL_W,
    TRIAGE_TEXT_W,
    _blend_triage,
    _fit_moment,
    _judge_window,
    _llm_workers,
    _parallel,
    _render_workers,
)
from medusacut.types import Candidate

_BIG = 10_000.0  # teto "sem limite" -> reproduz o comportamento de piso unico


def _row(start, score, triage):
    """(cand, words, text, triage_score) — so cand.score e triage importam aqui."""
    return (Candidate(start=start, end=start + 60.0, score=score), [], "", triage)


def test_llm_workers_default_and_override(monkeypatch):
    monkeypatch.delenv("MEDUSA_LLM_WORKERS", raising=False)
    assert _llm_workers() == 4
    monkeypatch.setenv("MEDUSA_LLM_WORKERS", "8")
    assert _llm_workers() == 8
    monkeypatch.setenv("MEDUSA_LLM_WORKERS", "0")  # invalido -> default
    assert _llm_workers() == 4
    monkeypatch.setenv("MEDUSA_LLM_WORKERS", "abc")
    assert _llm_workers() == 4


def test_parallel_returns_all_items_both_modes():
    items = list(range(8))
    sq = lambda x: x * x  # noqa: E731
    assert sorted(_parallel(items, sq, 4)) == [x * x for x in items]
    assert sorted(_parallel(items, sq, 1)) == [x * x for x in items]  # caminho serial
    assert list(_parallel([], sq, 4)) == []  # vazio
    assert list(_parallel([5], sq, 4)) == [25]  # 1 item cai no serial


def test_parallel_runs_concurrently():
    import time

    items = list(range(8))
    def slow(x):
        time.sleep(0.1)
        return x

    t = time.time()
    out = sorted(_parallel(items, slow, 4))
    dt = time.time() - t
    assert out == items
    assert dt < 0.6  # serial seria ~0.8s; com 4 workers fica bem abaixo


def test_fit_moment_keeps_window_in_range():
    assert _fit_moment(10.0, 30.0, 0.0, 60.0, 14.0, _BIG) == (10.0, 30.0)


def test_fit_moment_expands_short_window_around_center():
    rs, re_ = _fit_moment(20.0, 26.0, 0.0, 60.0, 14.0, _BIG)  # 6s -> 14s, centro 23
    assert re_ - rs == approx(14.0)
    assert (rs + re_) / 2 == approx(23.0)


def test_fit_moment_respects_bounds():
    rs, re_ = _fit_moment(1.0, 4.0, 0.0, 10.0, 14.0, _BIG)  # tmin > janela disponivel
    assert rs >= 0.0 and re_ <= 10.0
    rs, re_ = _fit_moment(58.0, 59.0, 0.0, 60.0, 14.0, _BIG)  # perto do fim
    assert re_ <= 60.0
    assert re_ - rs == approx(14.0)


def test_fit_moment_caps_long_clip_to_type_max():
    # historia? nao: clutch (tmax=50) num refino de 90s dentro de janela larga -> 50s
    rs, re_ = _fit_moment(100.0, 190.0, 0.0, 300.0, 15.0, 50.0)
    assert re_ - rs == approx(50.0)
    assert (rs + re_) / 2 == approx(145.0)  # encolhe em torno do centro


def test_fit_moment_allows_short_clutch():
    # clutch de 22s NAO e mais esticado pra 60s (piso por tipo = 15s)
    rs, re_ = _fit_moment(40.0, 62.0, 0.0, 120.0, 15.0, 50.0)
    assert re_ - rs == approx(22.0)


def test_judge_window_expands_when_isolated():
    # ancora de 60s (centro 110) -> janela larga ate ceil=180 (centro +-90)
    cand = Candidate(80.0, 140.0, 1.0)
    lo, hi = _judge_window(cand, [110.0], ceil=180.0, video_dur=600.0)
    assert (lo, hi) == approx((20.0, 200.0))


def test_judge_window_clamps_to_neighbor_midpoint():
    # vizinhos em 60 e 400 -> nao passa do meio-do-caminho (85 e 255)
    cand = Candidate(95.0, 125.0, 1.0)
    lo, hi = _judge_window(cand, [60.0, 110.0, 400.0], ceil=180.0, video_dur=600.0)
    assert lo == approx(85.0)        # (60+110)/2
    assert hi == approx(200.0)       # ctr+90 < (110+400)/2=255


def test_judge_window_clamps_to_video_bounds():
    cand = Candidate(100.0, 140.0, 1.0)
    lo, hi = _judge_window(cand, [120.0], ceil=180.0, video_dur=150.0)
    assert (lo, hi) == approx((30.0, 150.0))


def test_judge_window_never_shrinks_below_anchor():
    cand = Candidate(0.0, 200.0, 1.0)  # ancora maior que ceil
    lo, hi = _judge_window(cand, [100.0], ceil=60.0, video_dur=600.0)
    assert lo <= 0.0 and hi >= 200.0


def test_render_workers_opt_in_env(monkeypatch):
    monkeypatch.setenv("MEDUSA_RENDER_WORKERS", "3")
    assert _render_workers(5, cpu_bound=True) == 3  # env sobrescreve os dois regimes
    assert _render_workers(5, cpu_bound=False) == 3
    assert _render_workers(2) == 2  # nunca mais que o nº de cortes


def test_render_workers_cpu_bound_is_serial(monkeypatch):
    # optical-flow (facecam/scene_aware) satura a CPU -> serial, mesmo com muitos nucleos
    monkeypatch.delenv("MEDUSA_RENDER_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    assert _render_workers(5, cpu_bound=True) == 1


def test_render_workers_filter_path_parallel(monkeypatch):
    # caminho de filtro (blur/only): paraleliza ate ~metade dos nucleos, teto 4 e nº cortes
    monkeypatch.delenv("MEDUSA_RENDER_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    assert _render_workers(5, cpu_bound=False) == 4   # min(5, 4, 8//2=4)
    assert _render_workers(2, cpu_bound=False) == 2   # limitado pelo nº de cortes
    monkeypatch.setattr(os, "cpu_count", lambda: 4)
    assert _render_workers(5, cpu_bound=False) == 2   # min(5, 4, 4//2=2)


def test_render_workers_ignores_garbage_env(monkeypatch):
    monkeypatch.setenv("MEDUSA_RENDER_WORKERS", "abc")
    assert _render_workers(5, cpu_bound=True) == 1


def test_blend_rescues_silent_high_action_clip():
    # A: texto mediano mas sinal no topo (clutch silencioso). B: texto no topo,
    # pouca acao. So por texto, B venceria; o peso do sinal deve resgatar A.
    a = _row(start=10.0, score=100.0, triage=50.0)   # silencioso, muita acao
    b = _row(start=200.0, score=10.0, triage=60.0)   # papo, pouca acao
    c = _row(start=400.0, score=5.0, triage=10.0)    # filler
    # so por texto a ordem seria B, A, C
    assert sorted([a, b, c], key=lambda r: r[3], reverse=True)[0] is b
    # com o blend, A (sinal no topo) sobe na frente de B
    ranked = _blend_triage([a, b, c])
    assert ranked[0] is a
    assert ranked.index(a) < ranked.index(b)


def test_blend_falls_back_to_text_when_signal_flat():
    # sinal identico em todos -> ranking decidido so pela triagem de texto.
    rows = [_row(start=i * 100.0, score=5.0, triage=t) for i, t in enumerate([10, 90, 50])]
    ranked = _blend_triage(rows)
    assert [r[3] for r in ranked] == [90, 50, 10]


def test_blend_falls_back_to_signal_when_triage_all_failed():
    # triagem toda falhada (tudo 0) -> ranking decidido so pelo sinal.
    rows = [_row(start=i * 100.0, score=s, triage=0.0) for i, s in enumerate([3.0, 9.0, 6.0])]
    ranked = _blend_triage(rows)
    assert [r[0].score for r in ranked] == [9.0, 6.0, 3.0]


def test_blend_empty_is_empty():
    assert _blend_triage([]) == []


def test_blend_weights_sum_to_one():
    assert TRIAGE_TEXT_W + SIGNAL_W == approx(1.0)
