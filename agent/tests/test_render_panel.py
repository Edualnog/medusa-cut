"""Testes do segmento de painel dinamico (1-passada do layout facecam)."""

from __future__ import annotations

import os

from medusacut.reframe.layouts import ReframePlan
from medusacut.render.ffmpeg import dynamic_panel_segment


def test_static_panel_has_plain_crop(tmp_path):
    plan = ReframePlan(crop_w=608, crop_h=1080, target_w=1080, target_h=1280,
                       keyframes=[(0.0, 100.0)])
    seg = dynamic_panel_segment(
        plan, src_label="gsrc", out_label="game",
        sendcmd_path=str(tmp_path / "p.sendcmd"),
    )
    assert seg == "[gsrc]crop=608:1080:100.0:0,scale=1080:1280[game]"
    assert not os.path.exists(tmp_path / "p.sendcmd")  # estatico nao escreve sendcmd


def test_dynamic_panel_uses_named_crop_and_writes_sendcmd(tmp_path):
    plan = ReframePlan(crop_w=608, crop_h=1080, target_w=1080, target_h=1280,
                       keyframes=[(0.0, 100.0), (1.0, 400.0), (2.0, 250.0)])
    p = tmp_path / "p.sendcmd"
    seg = dynamic_panel_segment(
        plan, src_label="gsrc", out_label="game", sendcmd_path=str(p), crop_name="g",
    )
    # crop NOMEADO (pra o sendcmd nao mexer no outro crop do grafo)
    assert "crop@g=608:1080:100.0:0" in seg
    assert f"sendcmd=f='{p}'" in seg
    assert seg.startswith("[gsrc]") and seg.endswith("[game]")
    # sendcmd targeta so o crop nomeado, 1 linha por keyframe
    lines = p.read_text().strip().splitlines()
    assert lines == [
        "0.000 crop@g x 100.0;",
        "1.000 crop@g x 400.0;",
        "2.000 crop@g x 250.0;",
    ]


def test_squarify_expands_flat_cam_box():
    from medusacut.reframe.compose import _squarify_cam_box
    # box achatada em px (403x248 no 1920x1080, aspect ~1.6) -> ganha altura
    rect = _squarify_cam_box((0.01, 0.02, 0.22, 0.25), 1920, 1080, max_aspect=1.2)
    assert rect[0] == 0.01 and rect[2] == 0.22       # largura intacta
    assert rect[3] - rect[1] > 0.25 - 0.02           # mais alta que antes


def test_squarify_leaves_squarish_box():
    from medusacut.reframe.compose import _squarify_cam_box
    # box ja ~quadrada em px (300x300) -> inalterada
    rect = (0.0, 0.0, 300/1920, 300/1080)
    assert _squarify_cam_box(rect, 1920, 1080, max_aspect=1.2) == rect
