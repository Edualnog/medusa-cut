"""Transcricao com timestamps por palavra.

DOIS backends:
- **MLX** (Apple Silicon): roda na GPU/Neural Engine via `mlx-whisper` — ~3-4x mais
  rapido que CPU. Usado automaticamente em Mac arm64 quando disponivel.
- **faster-whisper** (ctranslate2, CPU): padrao no resto (Windows/Linux/Intel) e
  FALLBACK se o MLX falhar (ex.: nao bundlado/erro de Metal no binario empacotado).

Override do backend: `MEDUSA_WHISPER_BACKEND=mlx|faster|auto` (default auto).
Deps pesadas importadas DENTRO das funcoes. 1a chamada baixa o modelo (uma vez).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from medusacut.types import Word

_MODEL_CACHE: dict[tuple[str, str], object] = {}

# faster-whisper usa nomes curtos ("base"); o MLX usa repos do HuggingFace.
_MLX_REPOS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
}


def _use_mlx() -> bool:
    """MLX so faz sentido em Apple Silicon e quando o pacote esta disponivel."""
    backend = os.environ.get("MEDUSA_WHISPER_BACKEND", "auto").strip().lower()
    if backend == "faster":
        return False
    if backend == "mlx":
        return True
    import platform  # noqa: PLC0415

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    import importlib.util  # noqa: PLC0415

    return importlib.util.find_spec("mlx_whisper") is not None


_FASTER_DEVICE: tuple[str, str] | None = None


def _faster_device() -> tuple[str, str]:
    """(device, compute_type) do faster-whisper: usa **GPU NVIDIA (CUDA)** quando ha
    GPU + libs (cuBLAS/cuDNN) — ~5-10x mais rapido; senao CPU (int8). Cacheado.
    Override: MEDUSA_WHISPER_DEVICE=cuda|cpu."""
    global _FASTER_DEVICE
    if _FASTER_DEVICE is not None:
        return _FASTER_DEVICE
    forced = os.environ.get("MEDUSA_WHISPER_DEVICE", "").strip().lower()
    if forced == "cpu":
        _FASTER_DEVICE = ("cpu", "int8")
        return _FASTER_DEVICE
    want_cuda = forced == "cuda"
    if not want_cuda:
        try:
            import ctranslate2  # noqa: PLC0415

            want_cuda = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            want_cuda = False
    if want_cuda:
        # valida de fato: cria um modelo minusculo na GPU. Se faltar cuDNN/cuBLAS ou
        # o driver, cai pra CPU SEM quebrar (o usuario nao perde a geracao).
        try:
            from faster_whisper import WhisperModel  # noqa: PLC0415

            WhisperModel("tiny", device="cuda", compute_type="float16")
            print("[medusacut] transcricao na GPU NVIDIA (CUDA)", file=sys.stderr)
            _FASTER_DEVICE = ("cuda", "float16")
            return _FASTER_DEVICE
        except Exception as exc:  # noqa: BLE001
            print(f"[medusacut] CUDA indisponivel ({exc}); usando CPU", file=sys.stderr)
    _FASTER_DEVICE = ("cpu", "int8")
    return _FASTER_DEVICE


def _get_model(model_size: str, device: str, compute_type: str):
    key = (model_size, device, compute_type)
    if key not in _MODEL_CACHE:
        from faster_whisper import WhisperModel  # noqa: PLC0415

        _MODEL_CACHE[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
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
    # Default "base": rapido e a qualidade basta pro roteiro/legenda. WHISPER_MODEL muda.
    model_size = model_size or os.environ.get("WHISPER_MODEL", "base")
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

        if _use_mlx():
            try:
                return _transcribe_mlx(tmp.name, start, model_size, language)
            except Exception as exc:  # noqa: BLE001 — nunca derruba; cai pro CPU
                print(f"[medusacut] MLX falhou ({exc}); usando faster-whisper", file=sys.stderr)
        return _transcribe_faster(tmp.name, start, model_size, language, compute_type)
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


def _transcribe_faster(wav: str, start: float, model_size: str, language, compute_type: str) -> list[Word]:
    """Backend faster-whisper/ctranslate2: GPU NVIDIA (CUDA) se disponivel, senao CPU.
    beam_size=1 (greedy) + sem condicionar no texto anterior: mais rapido, sem perda
    relevante p/ fala de gameplay."""
    device, ctype = _faster_device()  # ignora o compute_type passado: decide por device
    model = _get_model(model_size, device, ctype)
    segments, _info = model.transcribe(
        wav, word_timestamps=True, language=language,
        beam_size=1, condition_on_previous_text=False,
    )
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            words.append(Word(text=w.word.strip(), start=start + w.start, end=start + w.end))
    return words


def _transcribe_mlx(wav: str, start: float, model_size: str, language) -> list[Word]:
    """Backend Apple Silicon (mlx-whisper, GPU/Neural Engine). Tempos relativos ao
    recorte -> somamos `start` p/ ficarem absolutos, igual ao faster-whisper."""
    import mlx_whisper  # noqa: PLC0415

    name = model_size.split("/")[-1]
    repo = model_size if "/" in model_size else _MLX_REPOS.get(name, _MLX_REPOS["base"])
    opts: dict = {"path_or_hf_repo": repo, "word_timestamps": True}
    if language:
        opts["language"] = language
    result = mlx_whisper.transcribe(wav, **opts)
    words: list[Word] = []
    for seg in result.get("segments", []):
        for w in seg.get("words") or []:
            words.append(Word(
                text=str(w.get("word", "")).strip(),
                start=start + float(w["start"]),
                end=start + float(w["end"]),
            ))
    return words


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
