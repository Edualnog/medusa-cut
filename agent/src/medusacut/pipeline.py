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

# Piso absoluto de duracao do corte qdo nenhum min_len e pedido na CLI — a faixa por
# TIPO de momento (hooks.moments) e quem manda; isto so evita corte degenerado.
HARD_FLOOR = 10.0

# Tamanho maximo do trecho de titulo no nome do arquivo (sem contar prefixo/extensao).
CLIP_NAME_MAX = 50


def clip_filename(idx: int, hook_text: str = "") -> str:
    """Nome do arquivo do corte derivado do HOOK (manchete da IA), nao 'clip_NN'.

    Ex.: hook "Clutch 1v5 no ultimo round!" -> "01-clutch-1v5-no-ultimo-round.mp4".
    O prefixo numerico (idx) preserva a ordem na pasta/biblioteca (que ordena por
    nome) e garante unicidade entre cortes que gerem o mesmo slug. Sem hook (ex.: IA
    desligada) cai pro classico "clip_NN.mp4".
    """
    import re
    import unicodedata

    # tira acentos (NFKD -> remove combinantes), minusculo, so [a-z0-9], resto vira '-'
    norm = unicodedata.normalize("NFKD", hook_text or "")
    ascii_text = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if len(slug) > CLIP_NAME_MAX:
        slug = slug[:CLIP_NAME_MAX].rstrip("-")
    if not slug:
        return f"clip_{idx:02d}.mp4"
    return f"{idx:02d}-{slug}.mp4"


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
    thumbnails: bool = True,
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

    lo = min_len if min_len is not None else fusion.MIN_LEN
    hi = max_len if max_len is not None else fusion.MAX_LEN

    # 3. transcricao UNICA do video + propostas do LLM por ROTEIRO. A energia perde
    # momento forte que nao e alto (historia engracada, reviravolta de RP, fail
    # silencioso); o LLM lendo o transcript acha. As propostas entram no pool junto.
    words_all = None
    proposals: list[Candidate] = []
    if score_virality or captions:
        import sys as _sys

        from medusacut.transcribe import whisper

        _report(progress, 0.48, "Transcrevendo o video…")
        try:
            words_all = whisper.transcribe_segment(wav_path, 0.0, media.duration)
        except Exception as exc:  # noqa: BLE001
            print(f"[medusacut] transcricao geral falhou ({exc})", file=_sys.stderr)
    if score_virality and words_all:
        from medusacut.hooks.propose import propose_candidates

        _report(progress, 0.52, "Lendo o roteiro (IA)…")
        ts_all = whisper.transcript_timestamped(words_all)
        proposals, _pu = propose_candidates(
            ts_all, game_context, media.duration, count=max_clips * 2, min_len=lo, max_len=hi
        )

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
    candidates = fusion.select_candidates(
        tracks, max_clips=pool, duration=media.duration, weights=weights,
        min_len=lo, max_len=hi,
    )
    # funde as propostas do LLM (roteiro) com as de energia no pool
    candidates = _merge_pool(proposals, candidates)

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
        thumbnails=thumbnails,
        final_count=max_clips,
        min_len=lo,
        max_len=hi,
        words_all=words_all,
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
    thumbnails: bool = True,
    final_count: int | None = None,
    min_len: float | None = None,
    max_len: float | None = None,
    words_all: list | None = None,
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

    # SO 2 layouts (decisao de produto): (A) facecam no terco superior + gameplay, ou
    # (B) gameplay tela cheia com blur. AUTO: procura o facecam SO nos cantos superiores
    # (95% dos casos) — achou -> A; nao achou -> B. Sem scene-aware, sem VLM, sem
    # optical-flow: mais simples e mais rapido.
    cuts = None  # sem deteccao de cena (poupa um decode do video inteiro)
    facecam_info = None
    if layout_name == "facecam_top_gameplay_bottom" and facecam_auto and facecam_box is None:
        import sys

        from medusacut.reframe import facecam as facecam_mod

        _report(progress, 0.0, "Detectando facecam (cantos superiores)…")
        detected = facecam_mod.detect_facecam(media.path)
        if detected:
            facecam_box = detected
            facecam_info = {"auto": True, "method": "yunet", "box": list(detected)}
        else:
            layout_name = "gameplay_blur"  # sem facecam -> foca 100% na acao (tela cheia)
            facecam_info = {"auto": True, "method": "none", "fallback": "gameplay_blur"}
            print(
                "[medusacut] facecam nao detectado nos cantos; usando gameplay_blur (tela cheia)",
                file=sys.stderr,
            )

    keep = final_count or len(candidates)
    # 3+6. transcrever (p/ legenda e/ou score) + analise viral 2 etapas -> re-rank.
    if (score_virality or captions) and audio_path:
        prepared, usage = _prepare_candidates(
            media, candidates, audio_path, game_context,
            score_virality=score_virality, final_count=keep, cache_dir=cache_dir,
            min_len=min_len, max_len=max_len, video_dur=media.duration, cuts=cuts,
            words_all=words_all, progress=_band(progress, 0.0, 0.5),
        )
        render_progress = _band(progress, 0.5, 1.0)
    else:
        prepared = [(c, None, None) for c in candidates[:keep]]
        usage = None
        render_progress = progress

    total = len(prepared)

    def _render_one(idx: int, cand, hook, words) -> Clip:
        """Renderiza 1 corte (layout + legenda) -> Clip. Independente por corte:
        nomes de arquivo/cache derivam de `clip_NN`, sem colisao entre threads."""
        import sys as _sys

        file_name = clip_filename(idx, hook.hook if hook else "")
        out_path = os.path.join(out_dir, file_name)
        cap_dir = os.path.join(cache_dir, f"{os.path.splitext(file_name)[0]}_cap")
        clip_dur = cand.end - cand.start
        # Faixas (alpha) fundidas no MESMO encode do render (1 passada): legenda + hook.
        caption_track = None
        if captions and words:
            from medusacut.caption import karaoke
            in_range = [w for w in words if w.end > cand.start and w.start < cand.end]
            try:
                caption_track = karaoke.build_caption_track(
                    in_range, clip_start=cand.start, clip_dur=clip_dur,
                    out_dir=cap_dir, y_frac=caption_y,
                )
            except Exception as exc:  # legenda nao deve derrubar o corte
                print(f"[medusacut] sem legenda em {file_name}: {exc}", file=_sys.stderr)
        # Hook (manchete): nos primeiros ~5s, no topo do gameplay (abaixo da facecam).
        hook_track = None
        hook_text = (hook.hook if hook else "").strip()
        if hook_text:
            from medusacut.caption import karaoke
            from medusacut.reframe.compose import PANEL_H
            top_y = (PANEL_H + 36) if layout_name == "facecam_top_gameplay_bottom" else 96
            try:
                hook_track = karaoke.build_hook_track(
                    hook_text, clip_dur=clip_dur, top_y=top_y, out_dir=cap_dir,
                )
            except Exception as exc:  # hook nao deve derrubar o corte
                print(f"[medusacut] sem hook em {file_name}: {exc}", file=_sys.stderr)
        _render_layout(media, cand, layout_name, facecam_corner, out_path, cache_dir,
                       facecam_box=facecam_box, overlays=[caption_track, hook_track])
        # Thumbnail (capa) 9:16: frame do corte + facecam (rosto real) + manchete.
        # Local, sem token, reusa o hook ja gerado. Extra: nunca derruba o corte.
        thumb_name = ""
        if thumbnails and hook_text:
            from medusacut import thumbnail
            stem = os.path.splitext(file_name)[0]
            thumb_path = os.path.join(out_dir, f"{stem}.jpg")
            made = thumbnail.build_thumbnail(
                media.path, cand.start, cand.end, hook_text,
                facecam_box=facecam_box, out_path=thumb_path, cache_dir=cap_dir,
            )
            if made:
                thumb_name = os.path.basename(made)
        return Clip(
            index=idx, start=cand.start, end=cand.end, score=cand.score, file=file_name,
            hook=hook.hook if hook else "",
            reason=hook.reason if hook else "",
            virality_score=hook.virality_score if hook else None,
            description=hook.description if hook else "",
            moment_type=hook.moment_type if hook else "",
            thumb=thumb_name,
        )

    # Render dos cortes em PARALELO. Os 2 layouts agora sao so filtergraph do ffmpeg
    # (sem optical-flow), que e single-thread no graph -> rodar cortes concorrentes usa
    # os nucleos ociosos e ganha ~40%. Override: MEDUSA_RENDER_WORKERS.
    # Ordem da saida preservada independente da ordem de conclusao.
    clips: list[Clip] = []
    if total:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        workers = _render_workers(total, cpu_bound=False)
        _report(render_progress, 0.0, f"Renderizando {total} corte(s) ({workers}x)…")
        results: dict[int, Clip] = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [
                ex.submit(_render_one, i, cand, hook, words)
                for i, (cand, hook, words) in enumerate(prepared, start=1)
            ]
            for fut in as_completed(futs):
                clip = fut.result()
                results[clip.index] = clip
                _report(render_progress, len(results) / total, f"Renderizado {len(results)}/{total}…")
        clips = [results[i] for i in sorted(results)]

    _write_manifest(out_dir, url=url, layout=layout_name, clips=clips, usage=usage, facecam=facecam_info)
    _report(render_progress, 1.0, "Pronto")
    return clips


# Quantos finalistas o juiz multimodal avalia alem do necessario (margem de re-rank).
JUDGE_BUFFER = 2
# Keyframes enviados ao juiz por corte.
KEYFRAMES = 4
# Peso da triagem de texto vs. evidencia de sinal (audio+movimento) ao montar a
# shortlist pro juiz multimodal. O sinal NAO pode ser descartado aqui: o motion
# track existe pra pegar clutch/explosao SILENCIOSOS, que rendem transcricao fraca
# (e triagem de texto baixa) — sem esse peso, o juiz que VE os frames nunca chega a
# ve-los. A triagem de texto ainda manda, mas o visual entra como desempate forte.
TRIAGE_TEXT_W = 0.65
SIGNAL_W = 0.35


def _prepare_candidates(
    media, candidates, audio_path, game_context, *, score_virality, final_count, cache_dir,
    min_len=None, max_len=None, video_dur=None, cuts=None, words_all=None, progress=None
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
        if words_all is not None:
            # ja temos a transcricao do video inteiro -> fatia (sem re-transcrever)
            words = [w for w in words_all if w.end > cand.start and w.start < cand.end]
        else:
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
    workers = _llm_workers()

    # etapa 1: triagem barata (texto) -> shortlist. PARALELO (chamadas de rede).
    def _do_triage(rec):
        cand, words, text = rec
        try:
            ts, u = hooks.triage_score(cand, text, game_context)
            return (cand, words, text, ts, u, None)
        except Exception as exc:  # noqa: BLE001
            return (cand, words, text, 0.0, None, exc)

    triaged = []  # (cand, words, text, triage_score)
    done = 0
    for cand, words, text, ts, u, exc in _parallel(records, _do_triage, workers):
        done += 1
        _report(progress, 0.4 + 0.2 * done / n if n else 0.6, f"Triando {done}/{n}…")
        if exc is not None:
            print(f"[medusacut] triagem falhou: {exc}", file=sys.stderr)
        if u is not None:
            usage_total = u if usage_total is None else usage_total + u
        triaged.append((cand, words, text, ts))
    shortlist = _blend_triage(triaged)[: final_count + JUDGE_BUFFER]

    # etapa 2: juiz forte multimodal (ve keyframes)
    from medusacut import frames
    from medusacut.hooks.moments import moment_bounds
    from medusacut.signals.fusion import MAX_LEN

    # envelope global por cima da faixa do TIPO: min_len pedido sobe o piso, max_len/
    # MAX_LEN baixa o teto. Sem min_len, o piso e HARD_FLOOR (deixa clutch ficar curto).
    floor = min_len if min_len is not None else HARD_FLOOR
    ceil = max_len if max_len is not None else MAX_LEN
    # O juiz escolhe as fronteiras DENTRO da janela; uma ancora de ~MIN_LEN trava o
    # tipo longo (story) em ~60s. Alarga a janela ate `ceil` em torno do centro, SEM
    # invadir o vizinho (para no meio do caminho pro centro do candidato ao lado).
    vid = video_dur if video_dur is not None else media.duration
    centers = sorted((c.start + c.end) / 2.0 for c in candidates)

    # etapa 2: juiz forte multimodal (ve keyframes). PARALELO: cada item faz
    # extract_keyframes (ffmpeg) + chamada de visao na rede — independentes entre si.
    def _do_judge(item):
        cand, words, _text, _ts = item
        hook = None
        usage = None
        exc_out = None
        try:
            jw_lo, jw_hi = _judge_window(cand, centers, ceil, vid)
            kf_dir = os.path.join(cache_dir, f"kf_{int(cand.start * 1000)}")
            n_kf = max(KEYFRAMES, min(8, round((jw_hi - jw_lo) / 25)))
            imgs = frames.extract_keyframes(media.path, jw_lo, jw_hi, n=n_kf, out_dir=kf_dir)
            jw_words = (
                [w for w in words_all if w.end > jw_lo and w.start < jw_hi]
                if words_all is not None else words
            )
            ts_text = whisper.transcript_timestamped(jw_words)
            win_cuts = [c for c in (cuts or []) if jw_lo < c < jw_hi]
            hook = hooks.judge_candidate(
                ts_text, imgs, game_context,
                win_start=jw_lo, win_end=jw_hi,
                anchor_s=(cand.start + cand.end) / 2.0,
                scene_cuts=win_cuts, min_len=min_len, max_len=max_len,
            )
            usage = hook.usage
            if hook.refined_start is not None and hook.refined_end is not None:
                tmin, tmax = moment_bounds(hook.moment_type, floor=floor, ceil=ceil)
                rs, re_ = _fit_moment(
                    hook.refined_start, hook.refined_end, jw_lo, jw_hi, tmin, tmax
                )
                cand = Candidate(rs, re_, cand.score)
        except Exception as exc:  # noqa: BLE001
            exc_out = exc
        # palavras da legenda: fatia a duracao FINAL (pode ter crescido/encolhido)
        final_words = [
            w for w in (words_all if words_all is not None else words)
            if w.end > cand.start and w.start < cand.end
        ]
        return (cand, hook, final_words, usage, exc_out)

    judged = []  # (cand, HookResult|None, words)
    m = len(shortlist)
    done = 0
    for cand, hook, final_words, usage, exc in _parallel(shortlist, _do_judge, workers):
        done += 1
        _report(progress, 0.6 + 0.4 * done / m if m else 1.0, f"Julgando {done}/{m} (visao)…")
        if exc is not None:
            print(f"[medusacut] juiz falhou: {exc}", file=sys.stderr)
        if usage is not None:
            usage_total = usage if usage_total is None else usage_total + usage
        judged.append((cand, hook, final_words))

    judged.sort(key=lambda t: t[1].virality_score if t[1] is not None else -1.0, reverse=True)
    return judged[:final_count], usage_total


def _blend_triage(triaged: list) -> list:
    """Ordena a triagem por uma MISTURA da nota de texto (LLM) com a evidencia de
    sinal (`cand.score` = audio+movimento), ambas normalizadas 0..1 dentro do pool.

    Sem isso, a shortlist pro juiz multimodal sairia so pela triagem de texto, e um
    clutch/explosao silencioso (transcricao fraca -> nota baixa) seria descartado
    antes do juiz VER os frames. Se uma das trilhas for plana (todas iguais ou
    triagem toda falhada), ela nao desempata — cai na outra.

    Entrada/saida: lista de (cand, words, text, triage_score).
    """
    if not triaged:
        return []
    t_norm = _minmax([t[3] for t in triaged])
    s_norm = _minmax([t[0].score for t in triaged])
    order = sorted(
        range(len(triaged)),
        key=lambda i: TRIAGE_TEXT_W * t_norm[i] + SIGNAL_W * s_norm[i],
        reverse=True,
    )
    return [triaged[i] for i in order]


def _minmax(xs: list[float]) -> list[float]:
    """Normaliza pra 0..1 por min-max; trilha plana vira tudo 0 (nao desempata)."""
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-9:
        return [0.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]


def _merge_pool(proposals: list[Candidate], energy: list[Candidate]) -> list[Candidate]:
    """Funde propostas do LLM (roteiro) + candidatos de energia num pool unico.

    Propostas recebem score = MEDIANA da energia (nao as penaliza no blend da
    shortlist, que mistura nota de texto e sinal). Candidato de energia que se
    sobrepoe a uma proposta e descartado — a proposta, mais intencional, prevalece.
    """
    if not proposals:
        return energy
    if energy:
        scores = sorted(c.score for c in energy)
        med = scores[len(scores) // 2]
        proposals = [Candidate(p.start, p.end, med) for p in proposals]
    pool = list(proposals)
    for c in energy:
        if not any(c.start < p.end and p.start < c.end for p in pool):
            pool.append(c)
    return pool


def _render_workers(n: int, *, cpu_bound: bool = True) -> int:
    """Quantos cortes renderizar em paralelo (limitado por `n`), ADAPTATIVO.

    Dois regimes (medido em 8 nucleos):
    - `cpu_bound=True` (optical-flow: facecam/scene_aware) — cada corte JA satura a CPU;
      concorrer so oversubscreve e fica MAIS LENTO (4 cortes 2x: 673s vs 566s serial).
      Fica SERIAL.
    - `cpu_bound=False` (filtro: gameplay_blur/only — ffmpeg single-thread no graph) —
      sobra nucleo ocioso; rodar em paralelo ganhou ~40% (3 cortes: 168s -> 102s). Liga
      ate ~metade dos nucleos (teto 4).
    `MEDUSA_RENDER_WORKERS` sobrescreve os dois regimes.
    """
    import os as _os

    env = (_os.environ.get("MEDUSA_RENDER_WORKERS") or "").strip()
    if env.isdigit() and int(env) > 0:
        return max(1, min(int(env), n))
    if cpu_bound:
        return 1
    cores = _os.cpu_count() or 4
    return max(1, min(n, 4, max(2, cores // 2)))


def _llm_workers() -> int:
    """Concorrencia das chamadas de IA (triagem/juiz). Sao I/O de REDE: rodar varias
    ao mesmo tempo derruba o tempo total sem saturar CPU. Default 4; override por
    `MEDUSA_LLM_WORKERS` (suba se o provedor aguentar, baixe se bater rate limit)."""
    import os as _os

    env = (_os.environ.get("MEDUSA_LLM_WORKERS") or "").strip()
    return int(env) if env.isdigit() and int(env) > 0 else 4


def _parallel(items, fn, workers):
    """Aplica `fn` a cada item; em paralelo (thread pool) quando workers>1. Faz yield
    dos resultados em ordem de CONCLUSAO (pra reportar progresso conforme termina)."""
    items = list(items)
    if workers <= 1 or len(items) <= 1:
        for it in items:
            yield fn(it)
        return
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as ex:
        futs = [ex.submit(fn, it) for it in items]
        for f in as_completed(futs):
            yield f.result()


def _judge_window(
    cand: Candidate, centers: list[float], ceil: float, video_dur: float
) -> tuple[float, float]:
    """Janela LARGA pro juiz: ate `ceil` em torno do centro da ancora, presa em
    [0, video_dur] e SEM passar do meio-do-caminho pro centro do vizinho (evita que
    duas ancoras proximas gerem cortes sobrepostos). Nunca menor que a ancora.
    """
    ctr = (cand.start + cand.end) / 2.0
    lefts = [c for c in centers if c < ctr - 1e-6]
    rights = [c for c in centers if c > ctr + 1e-6]
    lo_bound = 0.0 if not lefts else (max(lefts) + ctr) / 2.0
    hi_bound = video_dur if not rights else (min(rights) + ctr) / 2.0
    half = ceil / 2.0
    jw_lo = max(lo_bound, ctr - half)
    jw_hi = min(hi_bound, ctr + half)
    # nunca encolher abaixo da propria ancora
    jw_lo = max(0.0, min(jw_lo, cand.start))
    jw_hi = min(video_dur, max(jw_hi, cand.end))
    return jw_lo, jw_hi


def _fit_moment(
    rs: float, re_: float, lo: float, hi: float, tmin: float, tmax: float
) -> tuple[float, float]:
    """Prende a duracao do refino do LLM na faixa do TIPO [tmin, tmax], dentro da
    janela [lo, hi]. Cresce/encolhe em torno do centro; se a janela for menor que
    `tmin`, usa a janela toda.

    Substitui o antigo piso unico: agora um clutch curto NAO e esticado pra 60s, e
    uma historia longa NAO e cortada — cada tipo tem sua faixa (hooks.moments).
    """
    win = hi - lo
    tmax = min(tmax, win)
    tmin = min(tmin, tmax)
    length = re_ - rs
    target = max(tmin, min(length, tmax))
    if abs(target - length) < 1e-6:
        return rs, re_
    mid = (rs + re_) / 2.0
    rs = mid - target / 2.0
    re_ = mid + target / 2.0
    if rs < lo:
        rs, re_ = lo, lo + target
    if re_ > hi:
        re_, rs = hi, hi - target
    return rs, re_


def _resolve_layout(layout: str, facecam_corner: str | None, facecam_auto: bool = False) -> str:
    """SO 2 layouts: (A) facecam no terco superior — quando ha canto manual ou
    auto-deteccao; ou (B) gameplay tela cheia com blur. Se A for pedido mas a
    auto-deteccao nao achar facecam, o pipeline depois troca pra B. Nomes legados
    (gameplay_only/dynamic_gameplay) caem em B."""
    if layout == "facecam_top_gameplay_bottom" and (facecam_corner or facecam_auto):
        return "facecam_top_gameplay_bottom"
    return "gameplay_blur"


def _render_layout(
    media: Media,
    candidate: Candidate,
    layout_name: str,
    facecam_corner: str | None,
    out_path: str,
    cache_dir: str,
    *,
    facecam_box: tuple[float, float, float, float] | None = None,
    overlays: list[str] | None = None,
) -> None:
    """Despacha o render: SO 2 layouts. (A) facecam no terco superior + gameplay, ou
    (B) gameplay tela cheia com blur (foco 100% na acao). `overlays` (legenda + hook)
    sao fundidos no mesmo encode."""
    from medusacut.reframe import compose

    if layout_name == "facecam_top_gameplay_bottom":
        compose.render_facecam_layout(
            media, candidate, facecam_corner=facecam_corner,
            out_path=out_path, cache_dir=cache_dir, facecam_box=facecam_box,
            overlays=overlays,
        )
    else:  # gameplay_blur (e qualquer outro caindo no padrao seguro)
        compose.render_blur_fit(media, candidate, out_path=out_path, overlays=overlays)


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
