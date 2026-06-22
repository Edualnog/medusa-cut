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

# 1+2. motor (PyInstaller) + ffmpeg/ffprobe dentro de desktop/engine/ — mesmo passo do
# dev (`npm run engine`), reaproveitado aqui pra nao duplicar.
bash scripts/dev_engine.sh

# 3. instalador (+ publish opcional no CI)
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm run dist -- --publish "${PUBLISH:-never}"
echo "OK -> dist/"
