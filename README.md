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

## Licença e direitos (source-available)

Este repositório é **source-available**, não open source. O código fica público
por **transparência e auditoria de segurança** — coerente com a proposta
local-first e de privacidade do app: qualquer pessoa pode ler e confirmar que o
gameplay do usuário nunca sai da própria máquina.

Isso **não** concede licença de uso. Todos os direitos reservados: é proibido
usar, copiar, modificar, redistribuir ou criar produtos derivados/concorrentes a
partir deste código sem autorização escrita. Veja [`LICENSE`](LICENSE) para os
termos completos. Use o app pelos instaladores oficiais em medusaclip.com.

## Direção do produto

O Medusa Clip é um SaaS **local-first**:

- o site público será uma landing page com autenticação e download do aplicativo;
- o Supabase será usado para contas e autenticação (app **gratuito**, sem assinatura);
- vídeos, transcrição e renderização serão processados localmente pelo app desktop;
- cada usuário utilizará sua própria chave da OpenRouter para as etapas de IA;
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
  → ingestão e leitura de metadados
  → extração de áudio
  → sinais de energia e movimento
  → seleção dos melhores momentos
  → transcrição com timestamps por palavra
  → triagem e julgamento multimodal via OpenRouter
  → reframe vertical com acompanhamento da ação
  → legenda karaokê
  → renderização local com FFmpeg
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
- transcrição com `faster-whisper`;
- análise viral multimodal via OpenRouter;
- reframe dinâmico, detecção de facecam e legenda karaokê;
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
- a chave da OpenRouter é usada apenas pelo aplicativo e pelo provedor de IA;
- o usuário paga diretamente à OpenRouter pelo consumo dos modelos;
- o Supabase armazenará somente dados de conta, autenticação e acesso ao produto;
- nenhum vídeo precisa ser enviado para a infraestrutura do Medusa Clip.

**Custo na prática:** o gasto de IA é de **centavos por corte**. Num teste com os
modelos padrão (triagem `gpt-4o-mini`, juiz `gpt-4.1`), um vídeo de ~10 min gerou
4 cortes por **poucos centavos de dólar no total** — cerca de 1 centavo por corte.
O valor varia com o modelo escolhido (modelos mais baratos custam menos) e com o
tamanho do vídeo, e é cobrado direto pela OpenRouter na chave do usuário.

## Roadmap

1. Simplificar o site para landing page, autenticação Supabase e downloads.
2. Integrar login e controle de acesso do Supabase ao aplicativo desktop.
3. Corrigir e estabilizar o fluxo local completo em macOS.
4. Automatizar builds para macOS `arm64` e `x64`, Windows `x64` e Linux `x64`.
5. Assinar/notarizar os builds e publicar releases versionadas.
6. Implementar atualização automática e telemetria opcional, sem enviar vídeos.

## Licença

Projeto proprietário. Todos os direitos reservados.
