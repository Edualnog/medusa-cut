"""Orquestracao do tool pessoal. De um link do YouTube a cortes 9:16 na pasta out/.

Funcao sincrona e simples — uso pessoal, um video por vez. Sem fila/worker.

Marco 1: ingest -> preprocess -> sinal de audio -> fusao -> render (GameplayOnly).
As etapas de transcricao, gancho e facecam (passos 3/6/7 abaixo) chegam nos
Marcos 2-4; a assinatura ja contempla `game_context`/`layout` pra elas.
"""

from __future__ import annotations

import json
import os

from medusacut.types import Clip

# Duracao fixa de cada corte no Marco 1 (segundos).
DEFAULT_CLIP_LEN = 30.0


def generate_clips(
    url: str,
    *,
    out_dir: str = "out",
    max_clips: int = 10,
    layout: str = "facecam_top_gameplay_bottom",
    game_context: str = "",
) -> list[Clip]:
    """
    Fluxo (Marco 1 implementado; demais passos marcados):
      1. ingest YouTube (yt-dlp): baixa o video
      2. preprocess (ffmpeg): extrai audio, le fps/dimensoes
      3. transcribe (faster-whisper): timestamps por palavra            [M2]
      4. extrair sinais (audio_energy [+ scene_change/chat_velocity])
      5. fundir -> top-N candidatos
      6. >>> gerar GANCHO + score por candidato (hooks.generate_hook) <<< [M3]
      7. detectar facecam -> planejar layout                            [M4]
      8. render (ffmpeg) [+ legenda karaoke no M2]
      9. escrever clipes em out_dir/ + manifest.json

    Cada etapa atras de interface — trocar implementacao sem mexer aqui.
    """
    from medusacut.ingest import youtube
    from medusacut import preprocess
    from medusacut.reframe.layouts import get_layout
    from medusacut.render import ffmpeg as render
    from medusacut.signals import audio_energy, fusion

    os.makedirs(out_dir, exist_ok=True)
    cache_dir = os.path.join(out_dir, ".cache")

    # 1-2. baixar + extrair audio
    media = youtube.download(url, cache_dir)
    wav_path = preprocess.extract_audio(media, cache_dir)

    # 4-5. sinal de audio -> fusao -> candidatos
    audio_track = audio_energy.analyze(wav_path)
    candidates = fusion.select_candidates(
        [audio_track],
        max_clips=max_clips,
        clip_len=DEFAULT_CLIP_LEN,
        duration=media.duration,
    )

    # 7-8. render de cada candidato com o layout escolhido
    layout_impl = get_layout(layout)
    video_filter = layout_impl.video_filter(media)

    clips: list[Clip] = []
    for i, cand in enumerate(candidates, start=1):
        file_name = f"clip_{i:02d}.mp4"
        out_path = os.path.join(out_dir, file_name)
        render.render_clip(media, cand, video_filter, out_path)
        clips.append(
            Clip(
                index=i,
                start=cand.start,
                end=cand.end,
                score=cand.score,
                file=file_name,
            )
        )

    # 9. manifest
    _write_manifest(out_dir, url=url, layout=layout_impl.name, clips=clips)
    return clips


def _write_manifest(out_dir: str, *, url: str, layout: str, clips: list[Clip]) -> None:
    manifest = {
        "source": url,
        "layout": layout,
        "count": len(clips),
        "clips": [c.to_manifest_entry() for c in clips],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
