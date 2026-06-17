"""Orquestracao do tool pessoal. De um link do YouTube a cortes 9:16 na pasta out/.

Funcao sincrona e simples — uso pessoal, um video por vez. Sem fila/worker.

Fluxo atual: ingest -> preprocess -> sinal de audio -> fusao (duracao automatica)
-> render (GameplayOnly). Transcricao/gancho/facecam (passos 3/6/7) chegam nos
Marcos 2-4; a assinatura ja contempla `game_context`/`layout` pra elas.

Progresso: passe `progress(frac, label)` pra acompanhar 0..1 (CLI/painel local).
"""

from __future__ import annotations

import json
import os
from typing import Callable

from medusacut.types import Candidate, Clip, Media

# Callback de progresso: progress(fraction_0a1, rotulo_da_etapa).
Progress = Callable[[float, str], None]


def generate_clips(
    url: str,
    *,
    out_dir: str = "out",
    max_clips: int = 10,
    layout: str = "facecam_top_gameplay_bottom",
    game_context: str = "",
    facecam_corner: str | None = None,
    progress: Progress | None = None,
) -> list[Clip]:
    """
    Fluxo (duracao do corte decidida pelo conteudo; demais passos marcados):
      1. ingest YouTube (yt-dlp): baixa o video
      2. preprocess (ffmpeg): extrai audio, le fps/dimensoes
      3. transcribe (faster-whisper): timestamps por palavra            [M2]
      4. extrair sinais (audio_energy [+ scene_change/chat_velocity])
      5. fundir -> top-N candidatos (DURACAO AUTOMATICA)
      6. >>> gerar GANCHO + score por candidato (hooks.generate_hook) <<< [M3]
      7. detectar facecam -> planejar layout                            [M4]
      8. render (ffmpeg) [+ legenda karaoke no M2]
      9. escrever clipes em out_dir/ + manifest.json

    `progress` (keyword opcional) reporta 0..1 + rotulo pra UI/CLI. Cada etapa
    atras de interface.
    """
    from medusacut import preprocess
    from medusacut.ingest import youtube
    from medusacut.signals import audio_energy, fusion

    cache_dir = os.path.join(out_dir, ".cache")

    # 1. baixar (reporta 0.00 -> 0.45 conforme o yt-dlp baixa)
    _report(progress, 0.0, "Baixando video…")
    media = youtube.download(url, cache_dir, on_progress=_band(progress, 0.0, 0.45))

    # 2. extrair audio
    _report(progress, 0.45, "Extraindo audio…")
    wav_path = preprocess.extract_audio(media, cache_dir)

    # 4-5. sinal de audio -> fusao -> candidatos
    _report(progress, 0.55, "Medindo energia…")
    audio_track = audio_energy.analyze(wav_path)
    _report(progress, 0.65, "Selecionando os melhores momentos…")
    candidates = fusion.select_candidates(
        [audio_track], max_clips=max_clips, duration=media.duration
    )

    # 7-9. reframe + render + manifest (0.68 -> 1.00)
    return render_candidates(
        media,
        candidates,
        out_dir=out_dir,
        layout=layout,
        url=url,
        facecam_corner=facecam_corner,
        progress=_band(progress, 0.68, 1.0),
    )


def render_candidates(
    media: Media,
    candidates: list[Candidate],
    *,
    out_dir: str,
    layout: str,
    url: str,
    facecam_corner: str | None = None,
    progress: Progress | None = None,
) -> list[Clip]:
    """Reframe (segue a acao) + render de cada candidato + manifest.

    Separado de `generate_clips` de proposito: o painel local reusa o download e
    a analise (em cache) e so re-renderiza ao mexer nos parametros. `progress`
    reporta 0..1 ao longo do processo. `layout='gameplay_only'` faz crop central
    estatico; qualquer outro valor usa o enquadramento dinamico (segue a acao).
    """
    from medusacut.reframe import layouts
    from medusacut.render import ffmpeg as render

    os.makedirs(out_dir, exist_ok=True)
    cache_dir = os.path.join(out_dir, ".cache")
    dynamic = layout != "gameplay_only"
    layout_name = "dynamic_gameplay" if dynamic else "gameplay_only"

    total = len(candidates)
    clips: list[Clip] = []
    for i, cand in enumerate(candidates, start=1):
        _report(progress, (i - 1) / total if total else 1.0, f"Enquadrando e renderizando {i}/{total}…")
        plan = layouts.build_plan(
            media, cand, dynamic=dynamic, facecam_corner=facecam_corner
        )
        file_name = f"clip_{i:02d}.mp4"
        out_path = os.path.join(out_dir, file_name)
        render.render_clip(media, cand, plan, out_path, cache_dir=cache_dir)
        clips.append(
            Clip(
                index=i,
                start=cand.start,
                end=cand.end,
                score=cand.score,
                file=file_name,
            )
        )

    _write_manifest(out_dir, url=url, layout=layout_name, clips=clips)
    _report(progress, 1.0, "Pronto")
    return clips


def _report(progress: Progress | None, frac: float, label: str) -> None:
    if progress is not None:
        progress(min(1.0, max(0.0, frac)), label)


def _band(progress: Progress | None, lo: float, hi: float) -> Progress | None:
    """Reescala um progresso 0..1 de uma sub-etapa pra faixa [lo, hi] do total."""
    if progress is None:
        return None
    return lambda f, label: progress(lo + (hi - lo) * min(1.0, max(0.0, f)), label)


def _write_manifest(out_dir: str, *, url: str, layout: str, clips: list[Clip]) -> None:
    manifest = {
        "source": url,
        "layout": layout,
        "count": len(clips),
        "clips": [c.to_manifest_entry() for c in clips],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
