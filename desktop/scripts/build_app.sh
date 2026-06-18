#!/usr/bin/env bash
# Build do APP DESKTOP (Medusa Clip). Gera dist/Medusa Clip-*.dmg (Mac).
# Roda no SO alvo: Mac -> .dmg; Windows -> .exe (build separado, no Windows).
#
#   cd desktop && bash scripts/build_app.sh
#
# Pre-req: npm install (electron + electron-builder + @ffmpeg/@ffprobe-installer).
# Assinatura desligada (CSC_IDENTITY_AUTO_DISCOVERY=false / mac.identity=null) ate
# ter conta Apple Developer; o .dmg funciona com botao-direito -> Abrir.
set -euo pipefail
cd "$(dirname "$0")/.."   # desktop/

# 1. motor standalone (PyInstaller) -> agent/dist/medusacut-engine
( cd ../agent && VENV=.buildvenv bash scripts/build_engine.sh )

# 2. monta engine/ = motor + ffmpeg + ffprobe (static, do node_modules)
rm -rf engine && mkdir -p engine
cp -R ../agent/dist/medusacut-engine/. engine/
cp node_modules/@ffmpeg-installer/*/ffmpeg engine/ffmpeg
cp node_modules/@ffprobe-installer/*/ffprobe engine/ffprobe
chmod +x engine/medusacut-engine engine/ffmpeg engine/ffprobe

# 3. instalador
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm run dist
echo "OK -> dist/*.dmg"
