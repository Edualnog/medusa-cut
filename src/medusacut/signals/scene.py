"""Deteccao de corte de cena (PySceneDetect).

Usada pelo reframe: o enquadramento nao deve fazer panoramica ATRAVESSANDO um
corte de cena — ele "salta" pro novo enquadramento e suaviza dentro de cada cena.

`scenedetect` importado DENTRO da funcao (dep pesada). Falha vira lista vazia
(reframe cai pro comportamento sem cena).
"""

from __future__ import annotations


def detect_cuts(media_path: str, *, threshold: float = 27.0) -> list[float]:
    """Tempos ABSOLUTOS (s) dos cortes de cena do video. [] se nada/erro."""
    try:
        from scenedetect import ContentDetector, detect  # noqa: PLC0415

        scenes = detect(media_path, ContentDetector(threshold=threshold))
    except Exception:
        return []
    # `scenes` = [(start_tc, end_tc), …]; o corte e o inicio de cada cena apos a 1a.
    return [s[0].get_seconds() for s in scenes[1:]]
