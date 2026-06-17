"""Painel LOCAL do Medusa Cut (Streamlit).

Casca em cima de `pipeline` — NAO e um web app: roda so em 127.0.0.1, um usuario,
sincrono, sem API/fila/banco/auth/nuvem. E o "controle remoto" do CLI pra colar o
link e ir ajustando. Rode com `make ui`.

Reaproveita o download + a analise de audio em cache (st.session_state), entao
mexer nos parametros so re-roda fusao + render — sem rebaixar o video.
"""

from __future__ import annotations

import os

import streamlit as st

from medusacut import pipeline, preprocess
from medusacut.ingest import youtube
from medusacut.signals import audio_energy, fusion

st.set_page_config(page_title="Medusa Cut", page_icon="✂️", layout="wide")
st.title("✂️ Medusa Cut — painel local")
st.caption(
    "Ferramenta pessoal e local. Cola o link, ajusta, gera. "
    "Roda so no seu Mac (localhost) — sem nuvem, sem conta."
)

ss = st.session_state


def ensure_media(url: str, out_dir: str) -> None:
    """Baixa + analisa uma vez por URL; reusa do cache nos ajustes seguintes."""
    if ss.get("media_url") == url and "media" in ss:
        return
    cache_dir = os.path.join(out_dir, ".cache")
    with st.spinner("Baixando video (yt-dlp)…"):
        media = youtube.download(url, cache_dir)
    with st.spinner("Extraindo audio e medindo energia…"):
        wav = preprocess.extract_audio(media, cache_dir)
        track = audio_energy.analyze(wav)
    ss.media = media
    ss.track = track
    ss.media_url = url


with st.sidebar:
    st.header("Entrada")
    url = st.text_input("Link do YouTube", placeholder="https://youtube.com/watch?v=…")
    out_dir = st.text_input("Pasta de saida", value="out")

    st.header("Ajustes")
    max_clips = st.slider("Maximo de cortes", 1, 10, 3)
    clip_len = st.slider("Duracao do corte (s)", 10, 60, 30, step=5)

    gerar = st.button("Gerar cortes", type="primary", disabled=not url.strip())

if gerar:
    clean_url = url.strip()
    try:
        ensure_media(clean_url, out_dir)
        with st.spinner("Selecionando momentos e renderizando…"):
            candidates = fusion.select_candidates(
                [ss.track],
                max_clips=max_clips,
                clip_len=float(clip_len),
                duration=ss.media.duration,
            )
            clips = pipeline.render_candidates(
                ss.media,
                candidates,
                out_dir=out_dir,
                layout="gameplay_only",
                url=clean_url,
            )
        ss.clips = clips
        ss.out_dir = out_dir
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

# Resultados.
clips = ss.get("clips")
if clips:
    st.subheader(f"{len(clips)} corte(s) em {ss.out_dir}/")
    cols = st.columns(min(3, len(clips)))
    for i, clip in enumerate(clips):
        with cols[i % len(cols)]:
            path = os.path.join(ss.out_dir, clip.file)
            if os.path.exists(path):
                st.video(path)
            st.markdown(
                f"**{clip.file}**  \n"
                f"⏱ {clip.start:.1f}–{clip.end:.1f}s · "
                f"score {clip.score:+.2f}"
            )
    manifest_path = os.path.join(ss.out_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            st.download_button(
                "Baixar manifest.json", fh.read(), file_name="manifest.json"
            )
elif not gerar:
    st.info("Cola um link na barra lateral e clica em **Gerar cortes**.")
