"""Testes do parser de propostas do LLM (puro, sem LLM)."""

from __future__ import annotations

from medusacut.hooks.propose import parse_proposals


def _p(data, dur=1200.0, lo=60.0, hi=180.0, n=6):
    return parse_proposals(data, dur, min_len=lo, max_len=hi, max_count=n)


def test_valid_clips_parsed():
    cands = _p({"clips": [
        {"start_s": 100, "end_s": 200, "reason": "treta"},
        {"start_s": 400, "end_s": 500, "reason": "clutch"},
    ]})
    assert len(cands) == 2
    assert cands[0].start == 100 and cands[0].end == 200


def test_duration_forced_into_range():
    # 20s -> cresce pro min (60s) em torno do centro (110)
    cands = _p({"clips": [{"start_s": 100, "end_s": 120}]})
    assert len(cands) == 1
    assert abs((cands[0].end - cands[0].start) - 60.0) < 0.01
    assert abs(((cands[0].start + cands[0].end) / 2) - 110) < 0.01


def test_too_long_clipped_to_max():
    cands = _p({"clips": [{"start_s": 100, "end_s": 600}]})
    assert abs((cands[0].end - cands[0].start) - 180.0) < 0.01


def test_clamped_into_video_bounds():
    cands = _p({"clips": [{"start_s": 1180, "end_s": 1190}]}, dur=1200.0)
    assert cands[0].end <= 1200.0 and cands[0].start >= 0.0


def test_invalid_entries_dropped():
    cands = _p({"clips": [
        {"start_s": "x", "end_s": 200},
        {"reason": "sem tempos"},
        {"start_s": 100, "end_s": 200},
    ]})
    assert len(cands) == 1


def test_non_dict_or_missing_clips_returns_empty():
    assert _p({"nope": 1}) == []
    assert _p([1, 2, 3]) == []
    assert _p("texto") == []


def test_dedupe_overlapping():
    cands = _p({"clips": [
        {"start_s": 100, "end_s": 220},
        {"start_s": 110, "end_s": 230},  # quase igual -> removido
        {"start_s": 600, "end_s": 720},
    ]})
    assert len(cands) == 2


def test_max_count_cap():
    clips = [{"start_s": i * 200, "end_s": i * 200 + 100} for i in range(1, 6)]
    cands = _p({"clips": clips}, n=3)
    assert len(cands) == 3
