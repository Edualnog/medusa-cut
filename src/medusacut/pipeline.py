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
    facecam_box: tuple[float, float, float, float] | None = None,
    facecam_h: int = 640,
    caption_y: float = 0.80,
    score_virality: bool = True,
    captions: bool = True,
    progress: Progress | None = None,
) -> list[Clip]:
    """
    Fluxo (duracao do corte decidida pelo conteudo):
      1. ingest YouTube (yt-dlp): baixa o video
      2. preprocess (ffmpeg): extrai audio, le fps/dimensoes
      3. transcribe (faster-whisper): timestamps por palavra            [no score]
      4. extrair sinais (audio_energy [+ scene_change/chat_velocity])
      5. fundir -> top-N candidatos (DURACAO AUTOMATICA)
      6. >>> GANCHO + score de viralizacao (LLM) -> re-rank <<<
      7. detectar facecam -> planejar layout                            [M4 parcial]
      8. render (ffmpeg) [+ legenda karaoke no M2]
      9. escrever clipes em out_dir/ + manifest.json

    `score_virality` liga a etapa 6 (precisa de LLM_API_KEY no .env; se faltar ou
    falhar, cai pro ranking por energia). `progress` reporta 0..1 pra UI/CLI.
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

    # 6-9. score (LLM) + reframe + render + manifest (0.65 -> 1.00)
    return render_candidates(
        media,
        candidates,
        out_dir=out_dir,
        layout=layout,
        url=url,
        facecam_corner=facecam_corner,
        facecam_box=facecam_box,
        facecam_h=facecam_h,
        caption_y=caption_y,
        audio_path=wav_path,
        game_context=game_context,
        score_virality=score_virality,
        captions=captions,
        progress=_band(progress, 0.65, 1.0),
    )


def render_candidates(
    media: Media,
    candidates: list[Candidate],
    *,
    out_dir: str,
    layout: str,
    url: str,
    facecam_corner: str | None = None,
    facecam_box: tuple[float, float, float, float] | None = None,
    facecam_h: int = 640,
    caption_y: float = 0.80,
    audio_path: str | None = None,
    game_context: str = "",
    score_virality: bool = False,
    captions: bool = False,
    progress: Progress | None = None,
) -> list[Clip]:
    """Score de viralizacao + reframe + render + LEGENDA + manifest.

    Separado de `generate_clips` de proposito: o painel local reusa o download e
    a analise (em cache) e so re-pontua/re-renderiza ao mexer nos parametros.
    `score_virality` transcreve+pontua+re-ranqueia (LLM); `captions` queima a
    legenda karaoke. As duas reusam a mesma transcricao. Falha de LLM/whisper nao
    derruba o pipeline (cai pro ranking por energia / sem legenda).
    """
    os.makedirs(out_dir, exist_ok=True)
    cache_dir = os.path.join(out_dir, ".cache")
    layout_name = _resolve_layout(layout, facecam_corner)

    # 3+6. transcrever (p/ legenda e/ou score) + score (LLM) -> re-rank.
    if (score_virality or captions) and audio_path:
        prepared, usage = _prepare_candidates(
            candidates, audio_path, game_context,
            score_virality=score_virality, progress=_band(progress, 0.0, 0.5),
        )
        render_progress = _band(progress, 0.5, 1.0)
    else:
        prepared = [(c, None, None) for c in candidates]
        usage = None
        render_progress = progress

    total = len(prepared)
    clips: list[Clip] = []
    for i, (cand, hook, words) in enumerate(prepared, start=1):
        _report(render_progress, (i - 1) / total if total else 1.0, f"Renderizando corte {i}/{total}…")
        file_name = f"clip_{i:02d}.mp4"
        out_path = os.path.join(out_dir, file_name)
        _render_layout(media, cand, layout_name, facecam_corner, out_path, cache_dir,
                       facecam_box=facecam_box, facecam_h=facecam_h)
        if captions and words:
            _burn_captions(out_path, words, cand, cache_dir, caption_y)
        clips.append(
            Clip(
                index=i,
                start=cand.start,
                end=cand.end,
                score=cand.score,
                file=file_name,
                hook=hook.hook if hook else "",
                reason=hook.reason if hook else "",
                virality_score=hook.virality_score if hook else None,
            )
        )

    _write_manifest(out_dir, url=url, layout=layout_name, clips=clips, usage=usage)
    _report(render_progress, 1.0, "Pronto")
    return clips


def _prepare_candidates(candidates, audio_path, game_context, *, score_virality, progress):
    """Transcreve cada candidato (p/ legenda) e, se pedido, pontua viralizacao.

    Retorna [(cand_possivelmente_refinado, HookResult|None, words|None)]. Se houver
    score, ordena por viralizacao (sem nota por ultimo). Erro nao derruba: vira
    (cand, None, None).
    """
    import sys

    from medusacut.hooks import base as hooks
    from medusacut.transcribe import whisper

    total = len(candidates)
    out: list[tuple[Candidate, object | None, list | None]] = []
    usage_total = None
    for i, cand in enumerate(candidates, start=1):
        _report(progress, (i - 1) / total if total else 1.0, f"Transcrevendo e avaliando {i}/{total}…")
        words = None
        hook = None
        try:
            words = whisper.transcribe_segment(audio_path, cand.start, cand.end)
            if score_virality:
                from medusacut.signals.fusion import MIN_LEN

                text = whisper.transcript_text(words)
                hook = hooks.score_candidate(cand, text, game_context)
                if hook.refined_start is not None and hook.refined_end is not None:
                    rs, re_ = _floor_len(
                        hook.refined_start, hook.refined_end, cand.start, cand.end, MIN_LEN
                    )
                    cand = Candidate(rs, re_, cand.score)
        except Exception as exc:  # whisper/LLM/rede: nao derruba o pipeline
            print(f"[medusacut] corte {i} sem transcricao/score: {exc}", file=sys.stderr)
        if hook is not None and getattr(hook, "usage", None) is not None:
            usage_total = hook.usage if usage_total is None else usage_total + hook.usage
        out.append((cand, hook, words))

    if score_virality:
        out.sort(key=lambda t: t[1].virality_score if t[1] is not None else -1.0, reverse=True)
    return out, usage_total


def _floor_len(rs: float, re_: float, lo: float, hi: float, min_len: float) -> tuple[float, float]:
    """Garante que [rs, re_] tenha pelo menos `min_len`, encaixado em [lo, hi].

    Evita que o refino do LLM deixe o corte curto demais.
    """
    if re_ - rs >= min_len:
        return rs, re_
    span = min(min_len, hi - lo)
    mid = (rs + re_) / 2.0
    rs = mid - span / 2.0
    re_ = mid + span / 2.0
    if rs < lo:
        rs, re_ = lo, lo + span
    if re_ > hi:
        re_, rs = hi, hi - span
    return rs, re_


def _burn_captions(out_path, words, cand, cache_dir, caption_y=0.80):
    """Queima a legenda karaoke no clipe ja renderizado (substitui no lugar)."""
    import os as _os
    import sys

    from medusacut.caption import karaoke

    try:
        in_range = [w for w in words if w.end > cand.start and w.start < cand.end]
        cap_dir = _os.path.join(cache_dir, _os.path.splitext(_os.path.basename(out_path))[0] + "_cap")
        states = karaoke.render_caption_images(
            in_range, clip_start=cand.start, clip_dur=cand.end - cand.start,
            out_dir=cap_dir, y_frac=caption_y,
        )
        if not states:
            return
        tmp = out_path + ".cap.mp4"
        karaoke.burn(out_path, states, tmp)
        _os.replace(tmp, out_path)
    except Exception as exc:  # legenda nao deve derrubar o corte ja renderizado
        print(f"[medusacut] sem legenda em {_os.path.basename(out_path)}: {exc}", file=sys.stderr)


def _resolve_layout(layout: str, facecam_corner: str | None) -> str:
    """Normaliza o nome do layout; facecam sem canto definido cai pro dinamico."""
    if layout == "facecam_top_gameplay_bottom":
        return layout if facecam_corner else "dynamic_gameplay"
    if layout in ("gameplay_blur", "gameplay_only", "dynamic_gameplay"):
        return layout
    return "dynamic_gameplay"  # nome legado/desconhecido -> dinamico


def _render_layout(
    media: Media,
    candidate: Candidate,
    layout_name: str,
    facecam_corner: str | None,
    out_path: str,
    cache_dir: str,
    *,
    facecam_box: tuple[float, float, float, float] | None = None,
    facecam_h: int = 640,
) -> None:
    """Despacha o render conforme o layout resolvido."""
    from medusacut.reframe import compose, layouts
    from medusacut.render import ffmpeg as render

    if layout_name == "facecam_top_gameplay_bottom":
        compose.render_facecam_layout(
            media, candidate, facecam_corner=facecam_corner,
            out_path=out_path, cache_dir=cache_dir, dynamic=True,
            facecam_box=facecam_box, facecam_h=facecam_h,
        )
    elif layout_name == "gameplay_blur":
        compose.render_blur_fit(media, candidate, out_path=out_path)
    else:
        dynamic = layout_name != "gameplay_only"
        plan = layouts.build_plan(media, candidate, dynamic=dynamic, facecam_corner=facecam_corner)
        render.render_clip(media, candidate, plan, out_path, cache_dir=cache_dir)


def _report(progress: Progress | None, frac: float, label: str) -> None:
    if progress is not None:
        progress(min(1.0, max(0.0, frac)), label)


def _band(progress: Progress | None, lo: float, hi: float) -> Progress | None:
    """Reescala um progresso 0..1 de uma sub-etapa pra faixa [lo, hi] do total."""
    if progress is None:
        return None
    return lambda f, label: progress(lo + (hi - lo) * min(1.0, max(0.0, f)), label)


def _write_manifest(out_dir: str, *, url: str, layout: str, clips: list[Clip], usage=None) -> None:
    manifest = {
        "source": url,
        "layout": layout,
        "count": len(clips),
        "cost": usage.as_dict() if usage is not None else None,
        "clips": [c.to_manifest_entry() for c in clips],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
