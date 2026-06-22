#!/usr/bin/env bash
# Prepara o MOTOR pra rodar em DEV (npm start): builda o binario standalone do motor
# e copia ele + ffmpeg/ffprobe pra desktop/engine/ (essa pasta NAO vai pro git).
# Depois e so `npm start`. O build do instalador (build_app.sh) reaproveita este passo.
#
#   cd desktop && npm install && npm run engine && npm start
#
# Pre-req: `npm install` ja rodado em desktop/ (pega ffmpeg/ffprobe do node_modules) e
# python3.11 disponivel (a stack ML do motor nem sempre tem wheels pras versoes novas).
# Var: PYTHON (interpretador do motor, default python3.11).
set -euo pipefail
cd "$(dirname "$0")/.."   # desktop/

EXE=""
[ "${OS:-}" = "Windows_NT" ] && EXE=".exe"   # git-bash no Windows

# 1. motor standalone (PyInstaller) -> agent/dist/medusacut-engine
( cd ../agent && VENV="${VENV:-.buildvenv}" PYTHON="${PYTHON:-python3.11}" bash scripts/build_engine.sh )

# 2. monta engine/ = motor + ffmpeg + ffprobe (static, vindos do node_modules)
rm -rf engine && mkdir -p engine
cp -R "../agent/dist/medusacut-engine/." engine/
cp node_modules/@ffmpeg-installer/*/ffmpeg${EXE} "engine/ffmpeg${EXE}"
cp node_modules/@ffprobe-installer/*/ffprobe${EXE} "engine/ffprobe${EXE}"
chmod +x "engine/medusacut-engine${EXE}" "engine/ffmpeg${EXE}" "engine/ffprobe${EXE}" || true

echo "OK -> desktop/engine/ pronto. Agora rode: npm start"
