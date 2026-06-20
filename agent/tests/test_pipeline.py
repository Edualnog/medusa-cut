"""Testes de logica pura do pipeline (sem ffmpeg/LLM)."""

from __future__ import annotations

from pytest import approx

from medusacut.pipeline import SIGNAL_W, TRIAGE_TEXT_W, _blend_triage, _floor_len
from medusacut.types import Candidate


def _row(start, score, triage):
    """(cand, words, text, triage_score) — so cand.score e triage importam aqui."""
    return (Candidate(start=start, end=start + 60.0, score=score), [], "", triage)


def test_floor_len_keeps_long_enough_window():
    assert _floor_len(10.0, 30.0, 0.0, 60.0, 14.0) == (10.0, 30.0)


def test_floor_len_expands_short_window_around_center():
    rs, re_ = _floor_len(20.0, 26.0, 0.0, 60.0, 14.0)  # 6s -> 14s, centro 23
    assert re_ - rs == approx(14.0)
    assert (rs + re_) / 2 == approx(23.0)


def test_floor_len_respects_bounds():
    rs, re_ = _floor_len(1.0, 4.0, 0.0, 10.0, 14.0)  # min_len > janela disponivel
    assert rs >= 0.0 and re_ <= 10.0
    rs, re_ = _floor_len(58.0, 59.0, 0.0, 60.0, 14.0)  # perto do fim
    assert re_ <= 60.0
    assert re_ - rs == approx(14.0)


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
