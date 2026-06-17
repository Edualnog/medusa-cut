"""Painel LOCAL do Medusa Cut (Streamlit).

Casca em cima de `pipeline` — NAO e um web app: roda so em 127.0.0.1, um usuario,
sincrono, sem API/fila/banco/auth/nuvem. E o "controle remoto" do CLI pra colar o
link e ir ajustando. Rode com `make ui`.

Reaproveita o download + a analise de audio em cache (st.session_state), entao
mexer nos parametros so re-roda fusao + render — sem rebaixar o video.
"""

from __future__ import annotations

import json
import os
import time

import streamlit as st

from medusacut import pipeline, preprocess
from medusacut.ingest import youtube
from medusacut.reframe.saliency import FACECAM_RECTS
from medusacut.signals import audio_energy, fusion

st.set_page_config(page_title="Medusa Cut", page_icon="✂️", layout="wide")
st.title("✂️ Medusa Cut — painel local")
st.caption(
    "Pessoal e local. Cola o link, ajusta, gera cortes 9:16 pro TikTok. "
    "Roda so no seu Mac (localhost) — sem nuvem, sem conta."
)

ss = st.session_state


def ensure_media(url: str, out_dir: str, report) -> None:
    """Baixa + analisa uma vez por URL; reusa do cache nos ajustes seguintes."""
    if ss.get("media_url") == url and "media" in ss:
        report(0.65, "Usando download em cache…")
        return
    cache_dir = os.path.join(out_dir, ".cache")
    # download ocupa a faixa 0..0.55 do total
    media = youtube.download(
        url, cache_dir, on_progress=lambda f, label: report(0.55 * f, label)
    )
    report(0.58, "Extraindo audio…")
    wav = preprocess.extract_audio(media, cache_dir)
    report(0.63, "Medindo energia…")
    track = audio_energy.analyze(wav)
    ss.media = media
    ss.track = track
    ss.wav = wav
    ss.media_url = url


with st.sidebar:
    st.header("Entrada")
    url = st.text_input("Link do YouTube", placeholder="https://youtube.com/watch?v=…")
    out_dir = st.text_input("Pasta de saida", value="out")

    st.header("Ajustes")
    max_clips = st.slider("Maximo de cortes", 1, 10, 3)
    st.caption("A **duracao de cada corte e automatica** — o sistema decide pelo conteudo.")
    score_virality = st.checkbox(
        "Pontuar viralizacao (LLM)", value=True,
        help="Transcreve, da um gancho, nota de viralizacao 0-100 e re-ranqueia os cortes. Precisa da chave no .env.",
    )
    captions = st.checkbox(
        "Legenda karaoke (queimada)", value=True,
        help="Legenda palavra-a-palavra, estilo gamer (palavra ativa em amarelo).",
    )
    game_context = st.text_input(
        "Contexto do jogo/canal (opcional)", placeholder="ex.: Valorant, clutch 1v3",
        help="Ajuda o LLM a calibrar o gancho e a nota.",
    )
    with st.expander("Avancado"):
        min_len = st.slider("Duracao minima (s)", 5, 30, int(fusion.MIN_LEN))
        max_len = st.slider("Duracao maxima (s)", 30, 90, int(fusion.MAX_LEN))
        st.divider()
        _LAYOUTS = {
            "Gameplay (segue a acao)": "dynamic_gameplay",
            "Facecam em cima + gameplay embaixo": "facecam_top_gameplay_bottom",
            "Tela cheia + fundo desfocado": "gameplay_blur",
            "Crop central (estatico)": "gameplay_only",
        }
        layout_label = st.selectbox("Layout", list(_LAYOUTS), index=0)
        layout_value = _LAYOUTS[layout_label]
        _FACECAM = {
            "Nenhum / varia": None,
            "Topo esquerda": "tl",
            "Topo direita": "tr",
            "Baixo esquerda": "bl",
            "Baixo direita": "br",
        }
        facecam_label = st.selectbox(
            "Facecam (webcam do streamer)", list(_FACECAM), index=0,
            help="Necessario pro layout 'facecam em cima'. Tambem mascara esse canto no reframe dinamico.",
        )
        facecam_corner = _FACECAM[facecam_label]
        if layout_value == "facecam_top_gameplay_bottom" and facecam_corner is None:
            st.warning("Escolha o canto do facecam pra usar o layout 'facecam em cima'.")

        caption_y = st.slider(
            "Altura da legenda (0=topo, 1=base)", 0.50, 0.92, 0.80, 0.02,
            help="Maior = mais pra baixo, longe da cena.",
        )

        facecam_box = None
        facecam_h = 640
        if layout_value == "facecam_top_gameplay_bottom":
            preset = FACECAM_RECTS.get(facecam_corner or "tr", (0.62, 0.0, 1.0, 0.42))
            st.caption("Ajuste fino da caixa do facecam (fracao da tela):")
            fx = st.slider("Facecam X", 0.0, 0.95, float(preset[0]), 0.01)
            fy = st.slider("Facecam Y", 0.0, 0.95, float(preset[1]), 0.01)
            fw = st.slider("Facecam largura", 0.05, 1.0, float(preset[2] - preset[0]), 0.01)
            fh = st.slider("Facecam altura", 0.05, 1.0, float(preset[3] - preset[1]), 0.01)
            facecam_box = (fx, fy, min(1.0, fx + fw), min(1.0, fy + fh))
            facecam_h = st.slider("Altura do painel do rosto (px)", 360, 900, 640, 20)

    gerar = st.button("Gerar cortes", type="primary", disabled=not url.strip())

if gerar:
    clean_url = url.strip()
    bar = st.progress(0.0, text="Iniciando…")
    t0 = time.time()

    def report(frac: float, label: str) -> None:
        frac = min(1.0, max(0.0, frac))
        eta = ""
        elapsed = time.time() - t0
        if 0.03 < frac < 1.0:
            remain = int(elapsed * (1.0 - frac) / frac)
            eta = f" · ~{remain}s restantes"
        bar.progress(frac, text=f"{int(frac * 100)}% — {label}{eta}")

    try:
        ensure_media(clean_url, out_dir, report)
        report(0.66, "Selecionando os melhores momentos…")
        candidates = fusion.select_candidates(
            [ss.track],
            max_clips=max_clips,
            duration=ss.media.duration,
            min_len=float(min_len),
            max_len=float(max_len),
        )
        clips = pipeline.render_candidates(
            ss.media,
            candidates,
            out_dir=out_dir,
            layout=layout_value,
            url=clean_url,
            facecam_corner=facecam_corner,
            facecam_box=facecam_box,
            facecam_h=facecam_h,
            caption_y=caption_y,
            audio_path=ss.wav,
            game_context=game_context.strip(),
            score_virality=score_virality,
            captions=captions,
            progress=lambda f, label: report(0.66 + 0.34 * f, label),
        )
        report(1.0, "Pronto")
        ss.clips = clips
        ss.out_dir = out_dir
        try:
            with open(os.path.join(out_dir, "manifest.json"), encoding="utf-8") as fh:
                ss.cost = json.load(fh).get("cost")
        except (OSError, ValueError):
            ss.cost = None
        if not clips:
            st.warning(
                "Nenhum momento acima da media de energia. "
                "Tenta aumentar o numero de cortes ou outro trecho."
            )
    except RuntimeError as exc:
        # Erro de yt-dlp/ffmpeg vem pra tela como veio (sem contornar bloqueio).
        st.error(f"Falhou: {exc}")

# Contexto do video carregado: onde estao os picos de energia.
if "track" in ss:
    media = ss.media
    with st.expander("Energia de audio (z-score por janela)", expanded=False):
        st.line_chart({"energia": ss.track.scores})
        st.caption(
            f"Video: {media.width}×{media.height} · "
            f"{media.duration:.0f}s · {media.fps:.0f} fps"
        )

# Custo da geracao (LLM de viralizacao).
cost = ss.get("cost")
if cost:
    st.subheader("💸 Custo desta geracao (LLM)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Modelo", cost.get("model") or "—")
    c2.metric("Tokens totais", f"{cost.get('total_tokens', 0):,}")
    usd = cost.get("cost_usd")
    c3.metric("Custo (USD)", f"${usd:.4f}" if usd is not None else "n/d")
    st.caption(
        f"{cost.get('calls', 0)} chamada(s) · "
        f"entrada {cost.get('prompt_tokens', 0):,} + saida {cost.get('completion_tokens', 0):,} tokens"
        + ("" if usd is not None else " · custo nao retornado pela API")
    )

# Resultados.
clips = ss.get("clips")
if clips:
    st.subheader(f"{len(clips)} corte(s) em {ss.out_dir}/ — ordenados por viralizacao")
    cols = st.columns(min(3, len(clips)))
    for i, clip in enumerate(clips):
        with cols[i % len(cols)]:
            path = os.path.join(ss.out_dir, clip.file)
            if os.path.exists(path):
                st.video(path)
            if clip.hook:
                st.markdown(f"### {clip.hook}")
            if clip.virality_score is not None:
                st.progress(
                    clip.virality_score / 100.0,
                    text=f"🔥 Viralizacao: {clip.virality_score:.0f}/100",
                )
            if clip.reason:
                st.caption(f"_Por que prende:_ {clip.reason}")
            st.markdown(
                f"`{clip.file}` · ⏱ {clip.start:.1f}–{clip.end:.1f}s "
                f"({clip.end - clip.start:.0f}s) · energia {clip.score:+.2f}"
            )
    manifest_path = os.path.join(ss.out_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            st.download_button(
                "Baixar manifest.json", fh.read(), file_name="manifest.json"
            )
elif not gerar:
    st.info("Cola um link na barra lateral e clica em **Gerar cortes**.")
