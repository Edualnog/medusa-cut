#!/usr/bin/env bash
# Build do APP DESKTOP (Medusa Clip). Roda no SO alvo: Mac -> .dmg; Windows -> .exe;
# Linux -> .AppImage. NAO ha cross-compile (stack PyInstaller/ML + ffmpeg nativos).
#
#   cd desktop && bash scripts/build_app.sh
#
# Pre-req: npm install (electron + electron-builder + @ffmpeg/@ffprobe-installer).
# Assinatura desligada (CSC_IDENTITY_AUTO_DISCOVERY=false / mac.identity=null) ate
# ter conta Apple Developer; o instalador abre com botao-direito -> Abrir.
#
# Vars: PYTHON (interpretador do motor, default python3.11) · PUBLISH (electron-builder
# --publish: never|always; default never — o CI usa always pra subir na Release).
set -euo pipefail
cd "$(dirname "$0")/.."   # desktop/

EXE=""
[ "${OS:-}" = "Windows_NT" ] && EXE=".exe"   # git-bash no runner Windows

# 1. motor standalone (PyInstaller) -> agent/dist/medusacut-engine
( cd ../agent && VENV=.buildvenv bash scripts/build_engine.sh )

# 2. monta engine/ = motor + ffmpeg + ffprobe (static, do node_modules)
rm -rf engine && mkdir -p engine
cp -R "../agent/dist/medusacut-engine/." engine/
cp node_modules/@ffmpeg-installer/*/ffmpeg${EXE} "engine/ffmpeg${EXE}"
cp node_modules/@ffprobe-installer/*/ffprobe${EXE} "engine/ffprobe${EXE}"
chmod +x "engine/medusacut-engine${EXE}" "engine/ffmpeg${EXE}" "engine/ffprobe${EXE}" || true

# 3. instalador (+ publish opcional no CI)
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm run dist -- --publish "${PUBLISH:-never}"
echo "OK -> dist/"
