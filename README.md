<div align="center">

<img src="desktop/build/icon.png" alt="Medusa Clip" width="120" />

# Medusa Clip

**Cortes verticais 9:16 nível Opus Clip, feitos pra gameplay — grátis, open source e 100% no seu PC.**

[![Release](https://img.shields.io/github/v/release/Edualnog/medusa-cut?label=release&color=ffd11a)](https://github.com/Edualnog/medusa-cut/releases/latest)
[![License: AGPL-3.0](https://img.shields.io/github/license/Edualnog/medusa-cut?color=orange)](LICENSE)
[![Downloads](https://img.shields.io/github/downloads/Edualnog/medusa-cut/total?color=brightgreen)](https://github.com/Edualnog/medusa-cut/releases)
![Platforms](https://img.shields.io/badge/macOS%20%C2%B7%20Windows%20%C2%B7%20Linux-grey)
![No sign-up](https://img.shields.io/badge/sem%20cadastro-100%25%20local-success)

[**🌐 medusaclip.com**](https://medusaclip.com) · [**⬇️ Download**](#download) · [**💛 Apoiar**](https://medusaclip.com/apoiar)

<br />

<img src="web/public/desktop-app-preview.png" alt="Medusa Clip — aplicativo desktop" width="880" />

</div>

---

O **Medusa Clip** transforma gameplays longos em clipes verticais 9:16 prontos pra
TikTok, Reels e YouTube Shorts. O motor é **especializado em gameplay**: combina áudio,
movimento e visão pra achar clutch, fail, clímax e reação — com hook, legenda karaokê e
enquadramento automático.

Tudo roda **no seu computador**: o gameplay **nunca sobe pra nuvem**, **não tem cadastro
nem login**, e a IA usa a **sua própria chave**. É **grátis** e **open source**.

## ✨ Recursos

- **🎮 Especialista em gameplay** — não trata como vídeo de fala qualquer; lê áudio, movimento e frames pra reconhecer o que importa.
- **🔒 Sem cadastro, 100% local** — nada de login, e-mail ou senha; o vídeo é processado e fica no seu PC, sem servidor nosso.
- **🆓 Grátis e open source** — sob a licença AGPL-3.0, sem assinatura e sem paywall.
- **🔑 Sua chave de IA (BYO key)** — OpenRouter, OpenAI ou Anthropic; você paga centavos direto ao provedor.
- **✂️ Pós-produção automática** — hook (manchete), legenda karaokê palavra a palavra e reframe em 2 layouts (facecam + gameplay · ou foco na ação).
- **🖥️ Self-contained** — macOS, Windows e Linux; o instalador já traz o motor, `ffmpeg` e `ffprobe`. Sem instalar Python nem dependências.

## ⬇️ Download

Grátis. Os links apontam sempre pra **versão mais recente** — baixe pelo botão ou cole o comando.

**macOS (Apple Silicon / ARM64)** — [baixar `.dmg`](https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-mac-arm64.dmg)

```bash
curl -L -o MedusaClip.dmg https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-mac-arm64.dmg && open MedusaClip.dmg
```

**Windows 10/11 (x64)** — [baixar `.exe`](https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-win-x64.exe)

```powershell
iwr https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-win-x64.exe -OutFile MedusaClip.exe; .\MedusaClip.exe
```

**Linux (x64)** — [baixar `.AppImage`](https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-linux-x86_64.AppImage)

```bash
curl -L https://github.com/Edualnog/medusa-cut/releases/latest/download/MedusaClip-linux-x86_64.AppImage -o MedusaClip.AppImage && chmod +x MedusaClip.AppImage && ./MedusaClip.AppImage
```

Todas as versões em [Releases](https://github.com/Edualnog/medusa-cut/releases). Os builds
ainda **não são assinados** — na primeira abertura, no macOS clique com o botão direito
no app → **Abrir**; no Windows, em **Mais informações → Executar assim mesmo**.

## ⚙️ Como funciona

```text
vídeo local ou link público
  → ingestão (download h264 ≤1080p) e leitura de metadados
  → extração de áudio
  → transcrição com timestamps (GPU no Mac/Windows quando disponível; CPU senão)
  → sinais de energia e movimento → seleção dos melhores momentos
  → triagem + julgamento multimodal (OpenRouter / OpenAI / Anthropic), em paralelo
  → 2 layouts: facecam no topo + blur · ou gameplay tela cheia + blur
  → legenda karaokê + hook (manchete), no mesmo encode (FFmpeg local)
  → biblioteca local de clipes + manifest.json
```

## 🔐 Privacidade e custos

- O vídeo é processado e salvo **localmente** no seu computador.
- **Sem cadastro, sem conta, sem servidor nosso** — nenhum gameplay precisa sair do seu PC.
- A chave de IA fica **cifrada no seu dispositivo** e fala direto com o provedor escolhido.
- Você paga o consumo de IA **direto ao provedor** (OpenRouter / OpenAI / Anthropic).

**Custo na prática:** centavos por corte. Num teste com os modelos padrão, um vídeo de
~10 min gerou 4 cortes por **poucos centavos de dólar no total**. O valor varia com o
provedor/modelo e o tamanho do vídeo, cobrado direto pelo provedor na sua chave.

## 💛 Apoie o projeto

O Medusa Clip é grátis e open source, no espírito de projetos como o Blender. Se ele te
ajuda, considere apoiar (sempre opcional, nunca um paywall): **[medusaclip.com/apoiar](https://medusaclip.com/apoiar)**
— via **Pix** ou **cripto**. Compartilhar com quem joga e contribuir no GitHub também ajuda muito.

## 🛠️ Desenvolvimento

### Motor Python (`agent/`)

Requisitos: Python 3.11+, FFmpeg e FFprobe.

```bash
cd agent && make setup && make test
# CLI:
.venv/bin/medusacut "https://youtube.com/watch?v=..." --out out --clips 3
```

### Aplicativo desktop (`desktop/`)

```bash
cd desktop && npm install && npm start
# instalador do sistema atual:
bash scripts/build_app.sh
```

### Site (`web/`)

```bash
cd web && npm install && npm run dev
```

## 📁 Estrutura

```text
agent/      motor Python — pipeline de vídeo e testes (empacotado como binário)
desktop/    aplicativo Electron (o produto) + empacotamento multiplataforma
web/        landing estática (Next.js) — apresentação, downloads e página de apoio
docs/       arquitetura, setup e textos legais
```

## 📄 Licença

Open source sob **[GNU AGPL-3.0](LICENSE)**. Você pode usar, estudar, modificar e
redistribuir — desde que derivados (inclusive servidos pela rede) continuem abertos sob
a mesma licença. Componentes de terceiros nos builds (ex.: `ffmpeg`) seguem suas próprias
licenças. As marcas "Medusa Clip"/"medusaclip.com" e os logos não entram na licença de código.

<div align="center">
<sub>Feito pra criadores de gameplay · sem cadastro · no seu PC.</sub>
</div>
