"""Testes das partes puras da legenda karaoke (sem PIL/ffmpeg)."""

from __future__ import annotations

from pytest import approx

from medusacut.caption.karaoke import group_words, word_intervals
from medusacut.types import Word


def _w(text, s, e):
    return Word(text=text, start=s, end=e)


def test_group_splits_by_max_words():
    words = [_w(f"w{i}", i * 0.5, i * 0.5 + 0.4) for i in range(5)]
    groups = group_words(words, max_words=3, max_gap=10.0)
    assert [len(g) for g in groups] == [3, 2]


def test_group_splits_on_silence_gap():
    words = [_w("a", 0.0, 0.3), _w("b", 0.4, 0.7), _w("c", 3.0, 3.3)]
    groups = group_words(words, max_words=10, max_gap=0.7)
    assert [[w.text for w in g] for g in groups] == [["a", "b"], ["c"]]


def test_group_ignores_empty_words():
    words = [_w("a", 0.0, 0.3), _w("", 0.3, 0.3), _w("b", 0.4, 0.7)]
    groups = group_words(words, max_words=10, max_gap=5.0)
    assert [w.text for g in groups for w in g] == ["a", "b"]


def test_word_intervals_relative_and_clamped():
    phrase = [_w("a", 10.0, 10.5), _w("b", 11.0, 11.4), _w("c", 11.6, 13.0)]
    ivs = word_intervals(phrase, clip_start=10.0, clip_dur=2.5)
    # a fica ativa ate o inicio de b; b ate c; c ate seu fim (clampado em 2.5)
    assert ivs[0] == approx((0.0, 1.0))
    assert ivs[1] == approx((1.0, 1.6))
    assert ivs[2][0] == approx(1.6) and ivs[2][1] == approx(2.5)
    for t0, t1 in ivs:
        assert 0.0 <= t0 <= t1 <= 2.5 + 1e-9
