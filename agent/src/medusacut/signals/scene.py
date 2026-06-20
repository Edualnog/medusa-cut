"""Deteccao de corte de cena (PySceneDetect).

Usada pelo reframe: o enquadramento nao deve fazer panoramica ATRAVESSANDO um
corte de cena — ele "salta" pro novo enquadramento e suaviza dentro de cada cena.

`scenedetect` importado DENTRO da funcao (dep pesada). Falha vira lista vazia
(reframe cai pro comportamento sem cena).
"""

from __future__ import annotations


def detect_cuts(
    media_path: str, *, threshold: float = 27.0, downscale: int = 4
) -> list[float]:
    """Tempos ABSOLUTOS (s) dos cortes de cena do video. [] se nada/erro.

    Processa em resolucao REDUZIDA (`downscale`, ex.: 1/4 -> 480x270): a metrica de
    corte de cena e robusta a isso e fica ~varias vezes mais rapida que full-res 1080p.
    """
    try:
        from scenedetect import ContentDetector, SceneManager, open_video  # noqa: PLC0415

        video = open_video(media_path)
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))
        sm.auto_downscale = False
        sm.downscale = max(1, downscale)
        # Pula frames pra processar ~12fps efetivos (cortes de cena nao precisam de
        # 60fps; o decode de todo frame era o gargalo). frame_skip nao afeta o INICIO
        # da cena de forma relevante p/ alinhar layout.
        fps = float(getattr(video, "frame_rate", 0) or 0)
        frame_skip = max(0, round(fps / 12.0) - 1) if fps else 0
        sm.detect_scenes(video, frame_skip=frame_skip, show_progress=False)
        scenes = sm.get_scene_list()
    except Exception:
        return []
    # `scenes` = [(start_tc, end_tc), …]; o corte e o inicio de cada cena apos a 1a.
    return [s[0].get_seconds() for s in scenes[1:]]
