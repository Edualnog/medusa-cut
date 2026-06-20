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
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install . pyinstaller

cat > /tmp/medusacut_entry.py <<'PY'
import sys
from medusacut.local import run
sys.exit(run())
PY

"$VENV/bin/pyinstaller" --noconfirm --onedir --name medusacut-engine \
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime \
  --collect-all cv2 --collect-all av --collect-all yt_dlp --collect-all tokenizers \
  --collect-all huggingface_hub --collect-submodules medusacut \
  /tmp/medusacut_entry.py

echo "OK -> dist/medusacut-engine/"
