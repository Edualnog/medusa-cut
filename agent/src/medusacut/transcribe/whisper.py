"""Transcricao com timestamps por palavra (faster-whisper).

Interface fina de proposito: da pra trocar por whisper.cpp/mlx-whisper depois sem
mexer no pipeline. Em Apple Silicon roda em CPU (int8); a 1a chamada baixa o
modelo do HuggingFace (uma vez so).

`faster_whisper` importado DENTRO das funcoes (dep pesada).
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from medusacut.types import Word

_MODEL_CACHE: dict[tuple[str, str], object] = {}


def _get_model(model_size: str, compute_type: str):
    key = (model_size, compute_type)
    if key not in _MODEL_CACHE:
        from faster_whisper import WhisperModel  # noqa: PLC0415

        _MODEL_CACHE[key] = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    return _MODEL_CACHE[key]


def transcribe_segment(
    audio_path: str,
    start: float,
    end: float,
    *,
    model_size: str | None = None,
    language: str | None = None,
    compute_type: str = "int8",
) -> list[Word]:
    """Transcreve [start, end] do audio e devolve palavras com tempos ABSOLUTOS."""
    model_size = model_size or os.environ.get("WHISPER_MODEL", "small")
    language = language or os.environ.get("WHISPER_LANG") or None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", f"{start:.3f}", "-i", audio_path,
                "-t", f"{max(0.0, end - start):.3f}",
                "-ac", "1", "-ar", "16000", tmp.name,
            ],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou ao recortar audio: {proc.stderr.strip()}")

        model = _get_model(model_size, compute_type)
        segments, _info = model.transcribe(tmp.name, word_timestamps=True, language=language)

        words: list[Word] = []
        for seg in segments:
            for w in seg.words or []:
                words.append(Word(text=w.word.strip(), start=start + w.start, end=start + w.end))
        return words
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


def transcript_text(words: list[Word]) -> str:
    return " ".join(w.text for w in words).strip()


def transcript_timestamped(words: list[Word], *, gap: float = 1.2) -> str:
    """Transcricao com marca de TEMPO ABSOLUTO por linha, pro LLM escolher
    fronteiras coerentes. Quebra linha quando ha pausa > `gap`s entre palavras.

    Ex.: "[123.4s] de jeito nenhum a culpa e dele\n[131.0s] eu disse pra ele vir".
    """
    if not words:
        return ""
    lines: list[str] = []
    line: list[str] = []
    line_start = words[0].start
    prev_end = words[0].start
    for w in words:
        if line and w.start - prev_end > gap:
            lines.append(f"[{line_start:.1f}s] {' '.join(line)}")
            line = []
            line_start = w.start
        line.append(w.text)
        prev_end = w.end
    if line:
        lines.append(f"[{line_start:.1f}s] {' '.join(line)}")
    return "\n".join(lines)
