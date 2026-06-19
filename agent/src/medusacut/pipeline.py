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

# Quantos candidatos a fusao gera por corte final quando ha analise viral
# (o LLM escolhe os melhores dentre eles).
OVERSELECT_FACTOR = 3


def generate_clips(
    url: str,
    *,
    out_dir: str = "out",
    max_clips: int = 10,
    layout: str = "facecam_top_gameplay_bottom",
    game_context: str = "",
    facecam_corner: str | None = None,
    facecam_box: tuple[float, float, float, float] | None = None,
    facecam_auto: bool = False,
    facecam_h: int = 640,
    caption_y: float = 0.80,
    score_virality: bool = True,
    captions: bool = True,
    min_len: float | None = None,
    max_len: float | None = None,
    local_source: str | None = None,
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
    from medusacut.signals import audio_energy, fusion, motion

    cache_dir = os.path.join(out_dir, ".cache")
    os.makedirs(cache_dir, exist_ok=True)

    # 1. obter o video: arquivo local (upload do usuario) ou download por URL
    if local_source:
        _report(progress, 0.3, "Lendo video enviado…")
        media = youtube.probe_media(local_source)
    else:
        _report(progress, 0.0, "Baixando video…")
        media = youtube.download(url, cache_dir, on_progress=_band(progress, 0.0, 0.45))

    # 2. extrair audio
    _report(progress, 0.45, "Extraindo audio…")
    wav_path = preprocess.extract_audio(media, cache_dir)

    # 4-5. sinais (audio + movimento visual) -> fusao -> candidatos
    _report(progress, 0.55, "Medindo energia…")
    audio_track = audio_energy.analyze(wav_path)
    tracks = [audio_track]
    weights = [1.0]
    # Movimento visual: pega clutch/explosao silenciosos que o audio perde. Opcional —
    # se o cv2 falhar, segue so com audio (nao derruba o job).
    try:
        _report(progress, 0.6, "Medindo acao na tela…")
        motion_track = motion.analyze(media, audio_track)
        tracks.append(motion_track)
        weights.append(0.7)  # audio ainda manda; visual complementa
    except Exception as exc:  # noqa: BLE001
        print(f"[medusacut] sinal de movimento indisponivel ({exc}); so audio", file=__import__("sys").stderr)

    _report(progress, 0.65, "Selecionando os melhores momentos…")
    # Sobre-seleciona quando vai pontuar: a analise viral escolhe os melhores.
    pool = max_clips * OVERSELECT_FACTOR if score_virality else max_clips
    lo = min_len if min_len is not None else fusion.MIN_LEN
    hi = max_len if max_len is not None else fusion.MAX_LEN
    candidates = fusion.select_candidates(
        tracks, max_clips=pool, duration=media.duration, weights=weights,
        min_len=lo, max_len=hi,
    )

    # 6-9. analise viral (2 etapas) + reframe + render + manifest (0.65 -> 1.00)
    return render_candidates(
        media,
        candidates,
        out_dir=out_dir,
        layout=layout,
        url=url,
        facecam_corner=facecam_corner,
        facecam_box=facecam_box,
        facecam_auto=facecam_auto,
        facecam_h=facecam_h,
        caption_y=caption_y,
        audio_path=wav_path,
        game_context=game_context,
        score_virality=score_virality,
        captions=captions,
        final_count=max_clips,
        min_len=lo,
        max_len=hi,
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
    facecam_auto: bool = False,
    facecam_h: int = 640,
    caption_y: float = 0.80,
    audio_path: str | None = None,
    game_context: str = "",
    score_virality: bool = False,
    captions: bool = False,
    final_count: int | None = None,
    min_len: float | None = None,
    max_len: float | None = None,
    progress: Progress | None = None,
) -> list[Clip]:
    """Score de viralizacao + reframe + render + LEGENDA + manifest.

    Recebe candidatos (idealmente em excesso quando `score_virality`); a analise
    de duas etapas escolhe os melhores `final_count` pra render.

    Separado de `generate_clips` de proposito: o painel local reusa o download e
    a analise (em cache) e so re-pontua/re-renderiza ao mexer nos parametros.
    `score_virality` transcreve+pontua+re-ranqueia (LLM); `captions` queima a
    legenda karaoke. As duas reusam a mesma transcricao. Falha de LLM/whisper nao
    derruba o pipeline (cai pro ranking por energia / sem legenda).
    """
    os.makedirs(out_dir, exist_ok=True)
    cache_dir = os.path.join(out_dir, ".cache")
    layout_name = _resolve_layout(layout, facecam_corner, facecam_auto)

    # Cortes de cena (uma vez): o enquadramento dinamico salta neles em vez de varrer.
    cuts = None
    if layout_name in ("dynamic_gameplay", "facecam_top_gameplay_bottom"):
        from medusacut.signals import scene

        cuts = scene.detect_cuts(media.path)

    # Auto-deteccao do facecam (frente C): so no layout facecam, se pedido e sem box manual.
    facecam_info = None
    if layout_name == "facecam_top_gameplay_bottom" and facecam_auto and facecam_box is None:
        import sys

        from medusacut.reframe import facecam as facecam_mod

        _report(progress, 0.0, "Detectando facecam (rosto)…")
        detected = facecam_mod.detect_facecam(media.path)
        if detected:
            facecam_box = detected
            facecam_info = {"auto": True, "method": "yunet", "box": list(detected)}
        else:
            # Sem rosto estavel -> fallback VLM (pega VTuber/avatar/handcam que o
            # detector de rosto ignora). 1 chamada por job, so quando o rosto falha.
            from medusacut.frames import extract_keyframes
            from medusacut.reframe.facecam_vlm import detect_facecam_vlm

            _report(progress, 0.0, "Detectando facecam (visao)…")
            kf = extract_keyframes(
                media.path, 0.0, media.duration, n=3,
                out_dir=os.path.join(out_dir, "_facecam"),
            )
            vlm_box = detect_facecam_vlm(kf) if kf else None
            if vlm_box:
                facecam_box = vlm_box
                facecam_info = {"auto": True, "method": "vlm", "box": list(vlm_box)}
            else:
                # Sem rosto (nem YuNet nem VLM) -> nao force faixa de facecam vazia.
                # Cai pra tela cheia com fundo desfocado (decisao de produto).
                layout_name = "gameplay_blur"
                facecam_info = {"auto": True, "method": "none", "fallback": "gameplay_blur"}
                print(
                    "[medusacut] facecam nao detectado (rosto nem VLM); usando gameplay_blur (tela cheia)",
                    file=sys.stderr,
                )

    keep = final_count or len(candidates)
    # 3+6. transcrever (p/ legenda e/ou score) + analise viral 2 etapas -> re-rank.
    if (score_virality or captions) and audio_path:
        prepared, usage = _prepare_candidates(
            media, candidates, audio_path, game_context,
            score_virality=score_virality, final_count=keep, cache_dir=cache_dir,
            min_len=min_len, max_len=max_len, video_dur=media.duration,
            progress=_band(progress, 0.0, 0.5),
        )
        render_progress = _band(progress, 0.5, 1.0)
    else:
        prepared = [(c, None, None) for c in candidates[:keep]]
        usage = None
        render_progress = progress

    total = len(prepared)
    clips: list[Clip] = []
    for i, (cand, hook, words) in enumerate(prepared, start=1):
        _report(render_progress, (i - 1) / total if total else 1.0, f"Renderizando corte {i}/{total}…")
        file_name = f"clip_{i:02d}.mp4"
        out_path = os.path.join(out_dir, file_name)
        _render_layout(media, cand, layout_name, facecam_corner, out_path, cache_dir,
                       facecam_box=facecam_box, facecam_h=facecam_h, cuts=cuts)
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
                description=hook.description if hook else "",
            )
        )

    _write_manifest(out_dir, url=url, layout=layout_name, clips=clips, usage=usage, facecam=facecam_info)
    _report(render_progress, 1.0, "Pronto")
    return clips


# Quantos finalistas o juiz multimodal avalia alem do necessario (margem de re-rank).
JUDGE_BUFFER = 2
# Keyframes enviados ao juiz por corte.
KEYFRAMES = 4


def _prepare_candidates(
    media, candidates, audio_path, game_context, *, score_virality, final_count, cache_dir,
    min_len=None, max_len=None, video_dur=None, progress=None
):
    """Transcreve + (se pedido) pontua viralizacao em DUAS etapas e ranqueia.

    Etapa 1 (barata, texto): triagem de TODOS os candidatos -> shortlist.
    Etapa 2 (forte, multimodal): juiz ve keyframes -> gancho/nota/refino.
    Retorna ([(cand, HookResult|None, words|None)] com ate `final_count`), usage.
    """
    import sys

    from medusacut.hooks import base as hooks
    from medusacut.transcribe import whisper

    # transcreve todos (precisa pra triagem e/ou legenda) — reporta 0..0.4
    records = []  # (cand, words, text)
    n = len(candidates)
    for i, cand in enumerate(candidates, start=1):
        _report(progress, 0.4 * (i - 1) / n if n else 0.0, f"Transcrevendo {i}/{n}…")
        try:
            words = whisper.transcribe_segment(audio_path, cand.start, cand.end)
        except Exception as exc:
            print(f"[medusacut] corte {i} sem transcricao: {exc}", file=sys.stderr)
            words = []
        records.append((cand, words, whisper.transcript_text(words)))

    if not score_virality:
        out = [(c, None, w) for c, w, _ in records[:final_count]]
        return out, None

    usage_total = None

    # etapa 1: triagem barata (texto) -> shortlist
    triaged = []  # (cand, words, text, triage_score)
    for i, (cand, words, text) in enumerate(records, start=1):
        _report(progress, 0.4 + 0.2 * (i - 1) / n if n else 0.6, f"Triando {i}/{n}…")
        ts = 0.0
        try:
            ts, u = hooks.triage_score(cand, text, game_context)
            usage_total = u if usage_total is None else usage_total + u
        except Exception as exc:
            print(f"[medusacut] triagem falhou no corte {i}: {exc}", file=sys.stderr)
        triaged.append((cand, words, text, ts))
    triaged.sort(key=lambda t: t[3], reverse=True)
    shortlist = triaged[: final_count + JUDGE_BUFFER]

    # etapa 2: juiz forte multimodal (ve keyframes)
    from medusacut import frames
    from medusacut.signals.fusion import MIN_LEN

    floor = min_len if min_len is not None else MIN_LEN
    judged = []  # (cand, HookResult|None, words)
    m = len(shortlist)
    for i, (cand, words, text, _ts) in enumerate(shortlist, start=1):
        _report(progress, 0.6 + 0.4 * (i - 1) / m if m else 1.0, f"Julgando {i}/{m} (visao)…")
        hook = None
        try:
            kf_dir = os.path.join(cache_dir, f"kf_{int(cand.start * 1000)}")
            n_kf = max(KEYFRAMES, min(8, round((cand.end - cand.start) / 25)))
            imgs = frames.extract_keyframes(media.path, cand.start, cand.end, n=n_kf, out_dir=kf_dir)
            hook = hooks.judge_candidate(
                cand, text, imgs, game_context, min_len=min_len, max_len=max_len
            )
            if hook.usage is not None:
                usage_total = hook.usage if usage_total is None else usage_total + hook.usage
            if hook.refined_start is not None and hook.refined_end is not None:
                rs, re_ = _floor_len(hook.refined_start, hook.refined_end, cand.start, cand.end, floor)
                cand = Candidate(rs, re_, cand.score)
        except Exception as exc:
            print(f"[medusacut] juiz falhou no corte {i}: {exc}", file=sys.stderr)
        judged.append((cand, hook, words))

    judged.sort(key=lambda t: t[1].virality_score if t[1] is not None else -1.0, reverse=True)
    return judged[:final_count], usage_total


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


def _resolve_layout(layout: str, facecam_corner: str | None, facecam_auto: bool = False) -> str:
    """Normaliza o nome do layout. O split (facecam em cima) vale com canto manual
    OU com auto-deteccao; sem nenhum dos dois cai pro dinamico. (Se a auto-deteccao
    nao achar rosto, o pipeline depois troca pra gameplay_blur — tela cheia.)"""
    if layout == "facecam_top_gameplay_bottom":
        return layout if (facecam_corner or facecam_auto) else "dynamic_gameplay"
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
    cuts: list[float] | None = None,
) -> None:
    """Despacha o render conforme o layout resolvido."""
    from medusacut.reframe import compose, layouts
    from medusacut.render import ffmpeg as render

    if layout_name == "facecam_top_gameplay_bottom":
        compose.render_facecam_layout(
            media, candidate, facecam_corner=facecam_corner,
            out_path=out_path, cache_dir=cache_dir, dynamic=True,
            facecam_box=facecam_box, facecam_h=facecam_h, cuts=cuts,
        )
    elif layout_name == "gameplay_blur":
        compose.render_blur_fit(media, candidate, out_path=out_path)
    else:
        dynamic = layout_name != "gameplay_only"
        plan = layouts.build_plan(media, candidate, dynamic=dynamic, facecam_corner=facecam_corner, cuts=cuts)
        render.render_clip(media, candidate, plan, out_path, cache_dir=cache_dir)


def _report(progress: Progress | None, frac: float, label: str) -> None:
    if progress is not None:
        progress(min(1.0, max(0.0, frac)), label)


def _band(progress: Progress | None, lo: float, hi: float) -> Progress | None:
    """Reescala um progresso 0..1 de uma sub-etapa pra faixa [lo, hi] do total."""
    if progress is None:
        return None
    return lambda f, label: progress(lo + (hi - lo) * min(1.0, max(0.0, f)), label)


def _write_manifest(out_dir: str, *, url: str, layout: str, clips: list[Clip], usage=None, facecam=None) -> None:
    cost = None
    if usage is not None:
        from medusacut.llm import DEFAULT_JUDGE_MODEL, DEFAULT_TRIAGE_MODEL

        cost = usage.as_dict()
        cost["triage_model"] = os.environ.get("LLM_MODEL_TRIAGE", DEFAULT_TRIAGE_MODEL)
        cost["judge_model"] = os.environ.get("LLM_MODEL_JUDGE", DEFAULT_JUDGE_MODEL)
    manifest = {
        "source": url,
        "layout": layout,
        "count": len(clips),
        "cost": cost,
        "facecam": facecam,
        "clips": [c.to_manifest_entry() for c in clips],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
