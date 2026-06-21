# Medusa Clip

Aplicativo desktop para transformar gameplays longos em clipes verticais 9:16
prontos para TikTok, Reels e YouTube Shorts.

O processamento pesado acontece no computador do usuário. O motor combina sinais
de áudio e movimento, transcrição, análise multimodal, enquadramento automático e
legendas karaokê para encontrar e renderizar os melhores momentos.

## Download

Grátis. Cada instalador já traz o app, o motor de cortes, `ffmpeg` e `ffprobe`
embutidos — sem instalar Python nem dependências. Os links abaixo apontam sempre
para a **versão mais recente**; baixe pelo botão ou cole o comando no terminal.

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

Todas as versões: [Releases](https://github.com/Edualnog/medusa-cut/releases). Os builds
ainda **não são assinados** — na primeira abertura, no macOS clique com o botão direito
no app → **Abrir**; no Windows, em **Mais informações → Executar assim mesmo**.

## Licença (open source — AGPL-3.0)

O Medusa Clip é **open source**, sob a **GNU Affero General Public License v3.0**
(AGPL-3.0). Você pode usar, estudar, modificar e redistribuir o código — desde que
trabalhos derivados (inclusive quando oferecidos como serviço pela rede) **também
sejam liberados sob a AGPL-3.0**, mantendo o software livre. Veja [`LICENSE`](LICENSE)
para os termos completos.

Copyright (c) 2026 Medusa Clip. Os componentes de terceiros embutidos nos builds
oficiais (ex.: `ffmpeg`, bibliotecas Python) seguem suas próprias licenças. As marcas
"Medusa Clip" e "medusaclip.com" e os logos não são cobertos pela licença de código.

## Direção do produto

O Medusa Clip é um SaaS **local-first**:

- o site público será uma landing page com autenticação e download do aplicativo;
- o Supabase será usado para contas e autenticação (app **gratuito**, sem assinatura);
- vídeos, transcrição e renderização serão processados localmente pelo app desktop;
- cada usuário utilizará sua própria chave de IA (OpenRouter, OpenAI ou Anthropic) para as etapas de IA;
- não haverá VPS processando ou armazenando os vídeos dos usuários.

Essa arquitetura reduz custo operacional, preserva a privacidade dos arquivos e
aproveita CPU/GPU e o IP residencial do próprio usuário.

## Plataformas planejadas

| Plataforma | Arquitetura | Formato planejado |
|---|---|---|
| macOS | Apple Silicon (`arm64`) | `.dmg` |
| macOS | Intel (`x64`) | `.dmg` |
| Windows | `x64` | instalador `.exe` |
| Linux | `x64` | `.AppImage` e/ou `.deb` |

O motor Python é empacotado por plataforma com PyInstaller. O aplicativo Electron
inclui o motor, `ffmpeg` e `ffprobe`, portanto cada sistema precisa de seu próprio
pipeline de build.

## Como funciona

```text
vídeo local ou link público
  → ingestão (download h264 ≤1080p) e leitura de metadados
  → extração de áudio
  → transcrição com timestamps (GPU no Mac/Windows quando disponível; CPU senão)
  → sinais de energia e movimento → seleção dos melhores momentos
  → triagem + julgamento multimodal (OpenRouter / OpenAI / Anthropic), em paralelo
  → 2 layouts: facecam no topo + blur · ou gameplay tela cheia + blur
  → legenda karaokê + hook (manchete), renderizados no mesmo encode (FFmpeg local)
  → biblioteca local de clipes + manifest.json
```

## Estrutura do monorepo

```text
agent/      motor Python, pipeline de vídeo, worker legado e testes
desktop/    aplicativo Electron e empacotamento multiplataforma
web/        landing Next.js, autenticação Supabase e downloads por plataforma
supabase/   schemas e policies; inclui tabelas legadas do protótipo cloud
docs/       documentação de arquitetura e setup
```

## Estado atual

- motor de cortes local implementado;
- seleção por áudio e movimento;
- transcrição com GPU (MLX no Mac / CUDA no Windows) e fallback `faster-whisper` CPU;
- análise viral multimodal multi-provedor (OpenRouter / OpenAI / Anthropic), em paralelo;
- 2 layouts (facecam no topo + blur · gameplay tela cheia), detecção de facecam, legenda karaokê + hook;
- aplicativo Electron funcional, com login Supabase e onboarding de aceites;
- builds automatizados (GitHub Actions) para macOS `arm64`, Windows `x64` e Linux
  `x64`, publicados como release a cada tag `v*`, com auto-update;
- landing local-first com downloads por plataforma e auto-update ativos;
- pendente: assinatura/notarização dos builds (ainda sem assinatura).

## Desenvolvimento

### Motor Python

Requisitos: Python 3.11+, FFmpeg e FFprobe.

```bash
cd agent
make setup
make test
```

Execução pela CLI:

```bash
cd agent
.venv/bin/medusacut "https://youtube.com/watch?v=..." --out out --clips 3
```

### Aplicativo desktop

```bash
cd desktop
npm install
npm start
```

Para gerar o instalador no sistema atual:

```bash
cd desktop
bash scripts/build_app.sh
```

### Site

```bash
cd web
npm install
npm run dev
```

## Privacidade e custos

- o vídeo é processado e salvo localmente no computador do usuário;
- a chave de IA é usada apenas pelo aplicativo e pelo provedor escolhido;
- o usuário paga diretamente ao provedor (OpenRouter / OpenAI / Anthropic) pelo consumo;
- o Supabase armazenará somente dados de conta, autenticação e acesso ao produto;
- nenhum vídeo precisa ser enviado para a infraestrutura do Medusa Clip.

**Custo na prática:** o gasto de IA é de **centavos por corte**. Num teste com os
modelos padrão, um vídeo de ~10 min gerou 4 cortes por **poucos centavos de dólar no
total** — cerca de 1 centavo por corte. O valor varia com o provedor/modelo escolhido
(opções mais baratas custam menos) e com o tamanho do vídeo, cobrado direto pelo
provedor na chave do usuário.

## Roadmap

1. Simplificar o site para landing page, autenticação Supabase e downloads.
2. Integrar login e controle de acesso do Supabase ao aplicativo desktop.
3. Corrigir e estabilizar o fluxo local completo em macOS.
4. Automatizar builds para macOS `arm64` e `x64`, Windows `x64` e Linux `x64`.
5. Assinar/notarizar os builds e publicar releases versionadas.
6. Implementar atualização automática e telemetria opcional, sem enviar vídeos.

## Licença

Open source sob **AGPL-3.0** — ver a seção [Licença](#licença-open-source--agpl-30)
acima e o arquivo [`LICENSE`](LICENSE).
