"""Testes do z-score do sinal de movimento (puro, sem cv2)."""

from __future__ import annotations

from pytest import approx

from medusacut.signals.motion import _zscore


def test_zscore_centers_and_scales():
    z = _zscore([1.0, 2.0, 3.0])
    assert sum(z) == approx(0.0, abs=1e-9)       # media zero
    assert z[0] < 0 < z[2]                        # ordem preservada
    # variancia populacional = 1
    assert sum(v * v for v in z) / len(z) == approx(1.0, abs=1e-9)


def test_zscore_constant_is_zero():
    assert _zscore([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]


def test_zscore_empty():
    assert _zscore([]) == []
