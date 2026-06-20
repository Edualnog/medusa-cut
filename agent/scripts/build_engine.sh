#!/usr/bin/env bash
# Empacota o MOTOR num binario standalone (sem Python instalado) pro app desktop.
# Roda no SO alvo (Mac -> binario Mac; Windows -> .exe; sao builds separados).
#
#   bash agent/scripts/build_engine.sh
#
# Saida: dist/medusacut-engine/  (executavel + _internal/). A casca (Electron/Tauri)
# embute essa pasta e chama o binario com:
#   medusacut-engine <arquivo|link> --out <pasta> --key <OPENROUTER_KEY> [--clips N ...]
# O binario emite progresso em JSON por linha no stdout.
#
# NOTA: o ffmpeg/ffprobe NAO sao empacotados aqui (o motor chama o binario do sistema).
# Pra distribuir, inclua ffmpeg/ffprobe junto e ponha no PATH do processo.
set -euo pipefail

cd "$(dirname "$0")/.."   # agent/

# Interpretador fixavel (CI/local). Default python3.11: a stack ML (ctranslate2,
# onnxruntime, faster-whisper) nem sempre tem wheels pras versoes mais novas.
PYTHON="${PYTHON:-python3.11}"
command -v "$PYTHON" >/dev/null || PYTHON=python3
VENV="${VENV:-.buildvenv}"
"$PYTHON" -m venv "$VENV"

# Layout do venv difere por SO: Windows usa Scripts/python.exe; Unix usa bin/python.
# Chamamos tudo via "python -m pip" / "python -m PyInstaller" pra não depender de
# qual diretório/entrypoint existe.
PYBIN="$VENV/bin/python"
[ -f "$VENV/Scripts/python.exe" ] && PYBIN="$VENV/Scripts/python.exe"

"$PYBIN" -m pip install --upgrade pip >/dev/null
"$PYBIN" -m pip install . pyinstaller

ENTRY="$(mktemp -t medusacut_entry_XXXX.py)"
cat > "$ENTRY" <<'PY'
import sys
from medusacut.local import run
sys.exit(run())
PY

# Pacotes EXCLUÍDOS de propósito (peso morto — o app não usa):
#  - onnxruntime (~69MB): só seria usado pelo VAD Silero; transcrevemos SEM vad_filter.
#  - boto3/botocore (~25MB): só o worker da VPS (abandonada) usava, p/ R2.
# ATENÇÃO: `av` (PyAV) NÃO pode sair — o faster-whisper usa PyAV pra DECODIFICAR o
# áudio na transcrição (testado: sem ele, "No module named 'av'" e cortes sem legenda).
# Sempre revisar este enxugamento ao mexer em transcribe/scene/reframe.
"$PYBIN" -m PyInstaller --noconfirm --onedir --name medusacut-engine \
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all av \
  --collect-all cv2 --collect-all yt_dlp --collect-all tokenizers \
  --collect-all huggingface_hub --collect-all anthropic --collect-submodules medusacut \
  --exclude-module onnxruntime \
  --exclude-module boto3 --exclude-module botocore \
  "$ENTRY"

echo "OK -> dist/medusacut-engine/"
