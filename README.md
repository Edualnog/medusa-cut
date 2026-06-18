# Medusa Clip

Aplicativo desktop para transformar gameplays longos em clipes verticais 9:16
prontos para TikTok, Reels e YouTube Shorts.

O processamento pesado acontece no computador do usuário. O motor combina sinais
de áudio e movimento, transcrição, análise multimodal, enquadramento automático e
legendas karaokê para encontrar e renderizar os melhores momentos.

## Direção do produto

O Medusa Clip é um SaaS **local-first**:

- o site público será uma landing page com autenticação e download do aplicativo;
- o Supabase será usado para contas, autenticação e controle de acesso/assinatura;
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
web/        site Next.js; será reduzido para landing, autenticação e downloads
supabase/   schemas e policies; inclui tabelas legadas do protótipo cloud
docs/       documentação de arquitetura e setup
```

## Estado atual

- motor de cortes local implementado;
- seleção por áudio e movimento;
- transcrição com `faster-whisper`;
- análise viral multimodal via OpenRouter;
- reframe dinâmico, detecção de facecam e legenda karaokê;
- aplicativo Electron funcional e build `.dmg` sem assinatura;
- protótipo web/cloud ainda presente no código e pendente de simplificação;
- autenticação Supabase já existe na web; login desktop, licenciamento e builds
  automatizados ainda estão pendentes.

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

## Roadmap

1. Simplificar o site para landing page, autenticação Supabase e downloads.
2. Integrar login e controle de acesso do Supabase ao aplicativo desktop.
3. Corrigir e estabilizar o fluxo local completo em macOS.
4. Automatizar builds para macOS `arm64` e `x64`, Windows `x64` e Linux `x64`.
5. Assinar/notarizar os builds e publicar releases versionadas.
6. Implementar atualização automática e telemetria opcional, sem enviar vídeos.

## Licença

Projeto proprietário. Todos os direitos reservados.
