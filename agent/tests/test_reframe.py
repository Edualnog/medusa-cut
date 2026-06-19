"""Testes das partes puras do reframe (crop/suavizacao). Sem video nem OpenCV."""

from __future__ import annotations

from medusacut.reframe.layouts import (
    centers_to_keyframes,
    crop_dims,
    smooth_centers,
)
from medusacut.reframe.saliency import (
    _center_weight,
    _weighted_center,
    facecam_rect,
)


def test_crop_dims_169_source_gives_916_column():
    cw, ch = crop_dims(1280, 720)
    assert ch == 720
    assert cw % 2 == 0
    # razao ~ 9:16
    assert abs(cw / ch - 9 / 16) < 0.01


def test_crop_dims_are_even():
    cw, ch = crop_dims(1920, 1080)
    assert cw % 2 == 0 and ch % 2 == 0


def test_facecam_rect_presets():
    assert facecam_rect("tr") == (0.62, 0.0, 1.0, 0.42)
    assert facecam_rect("TL")[0] == 0.0  # case-insensitive
    assert facecam_rect(None) is None
    assert facecam_rect("xx") is None


def test_smooth_centers_ema():
    out = smooth_centers([0.0, 1.0, 1.0, 1.0], alpha=0.5)
    assert out == [0.0, 0.5, 0.75, 0.875]


def test_centers_to_keyframes_clamps_inside_frame():
    samples = [(0.0, 0.5), (1.0, 0.0), (2.0, 1.0)]
    kf = centers_to_keyframes(samples, width=1000, crop_w=300, alpha=1.0)
    xs = [x for _, x in kf]
    # 0.5 -> 350 ; 0.0 -> -150 (clamp 0) ; 1.0 -> 850 (clamp width-crop=700)
    assert xs == [350.0, 0.0, 700.0]
    for _, x in kf:
        assert 0.0 <= x <= 700.0


def test_centers_to_keyframes_resets_on_scene_cut():
    # movimento salta de esquerda (0.0) pra direita (1.0) num corte de cena.
    samples = [(0.0, 0.0), (1.0, 0.0), (2.0, 1.0), (3.0, 1.0)]
    no_cut = dict((round(t), x) for t, x in centers_to_keyframes(samples, 1000, 300, alpha=0.25))
    with_cut = dict(
        (round(t), x) for t, x in centers_to_keyframes(samples, 1000, 300, alpha=0.25, cuts=[2.0])
    )
    # sem corte: EMA deixa o ponto pos-salto atrasado; com corte: salta de vez
    assert with_cut[2] > no_cut[2]
    assert with_cut[2] == 700.0  # snap total (preso na borda)


def test_centers_to_keyframes_empty_falls_back_to_center():
    kf = centers_to_keyframes([], width=1000, crop_w=300)
    assert kf == [(0.0, 350.0)]


# --- tracking novo: vies de centro + lock-on (usa numpy, sem video) ---

def test_center_weight_peaks_at_middle():
    import numpy as np

    w = _center_weight(np, 9)
    assert w.argmax() == 4              # pico no meio
    assert w[0] < w[4] and w[-1] < w[4]  # bordas pesam menos
    assert abs(w[0] - w[-1]) < 1e-6      # simetrico


def test_weighted_center_holds_previous_when_idle():
    import numpy as np

    col = np.zeros(20, dtype=np.float32)  # frame parado (sem movimento)
    assert _weighted_center(np, col, _center_weight(np, 20), 0.7) == 0.7


def test_weighted_center_biases_edge_action_toward_center():
    import numpy as np

    col = np.zeros(21, dtype=np.float32)
    col[-1] = 1.0  # toda a energia na borda direita
    w = _center_weight(np, 21)
    cx = _weighted_center(np, col, w, 0.5)
    assert 0.5 < cx < 1.0  # move pra acao, mas o vies de centro + lock seguram


def test_weighted_center_symmetric_stays_centered():
    import numpy as np

    col = np.zeros(21, dtype=np.float32)
    col[0] = col[-1] = 1.0  # energia simetrica nas duas bordas
    cx = _weighted_center(np, col, _center_weight(np, 21), 0.5)
    assert abs(cx - 0.5) < 1e-6
