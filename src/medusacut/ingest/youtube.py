"""Ingest: baixa o video do YouTube com yt-dlp e le os metadados.

Regra do projeto: NAO contornar bloqueios. Se o yt-dlp falhar, propagamos um
erro claro pra o dono decidir — nada de fallback/scraping alternativo.
"""

from __future__ import annotations

import os

from medusacut.types import Media


def download(url: str, dest_dir: str) -> Media:
    """Baixa `url` para `dest_dir` e devolve um Media com fps/dimensoes/duracao.

    Deps pesadas (yt_dlp) importadas aqui dentro, nunca no topo do modulo.
    """
    import yt_dlp  # noqa: PLC0415 — heavy dep, import local de proposito

    os.makedirs(dest_dir, exist_ok=True)
    outtmpl = os.path.join(dest_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        # melhor video + melhor audio, remuxado pra mp4 (ffmpeg ja instalado)
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = _resolve_path(ydl, info)
    except yt_dlp.utils.DownloadError as exc:
        # Reporta o erro exato (sem tentar burlar bloqueio).
        raise RuntimeError(f"yt-dlp falhou ao baixar {url!r}: {exc}") from exc

    if not path or not os.path.exists(path):
        raise RuntimeError(
            f"download concluiu mas o arquivo nao foi encontrado para {url!r}"
        )

    fps, width, height, duration = _probe(path, info)
    return Media(path=path, fps=fps, width=width, height=height, duration=duration)


def _resolve_path(ydl, info: dict) -> str | None:
    """Caminho final do arquivo (apos merge), de forma robusta."""
    requested = info.get("requested_downloads")
    if requested:
        fp = requested[0].get("filepath")
        if fp:
            return fp
    return ydl.prepare_filename(info)


def _probe(path: str, info: dict) -> tuple[float, int, int, float]:
    """Le fps/dimensoes/duracao. Prefere ffprobe; cai no info dict do yt-dlp."""
    import json
    import subprocess

    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=avg_frame_rate,width,height:format=duration",
                "-of", "json", path,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        data = json.loads(out)
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        fps = _parse_fraction(stream.get("avg_frame_rate")) or float(info.get("fps") or 30.0)
        width = int(stream.get("width") or info.get("width") or 0)
        height = int(stream.get("height") or info.get("height") or 0)
        duration = float(fmt.get("duration") or info.get("duration") or 0.0)
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        fps = float(info.get("fps") or 30.0)
        width = int(info.get("width") or 0)
        height = int(info.get("height") or 0)
        duration = float(info.get("duration") or 0.0)

    if width <= 0 or height <= 0 or duration <= 0:
        raise RuntimeError(
            f"metadados invalidos apos download (w={width}, h={height}, dur={duration})"
        )
    return fps, width, height, duration


def _parse_fraction(value: str | None) -> float | None:
    """'30000/1001' -> 29.97. Retorna None se nao der pra parsear."""
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else None
        return float(value)
    except ValueError:
        return None
