# Roadmap técnico — Medusa Clip local-first

> App **gratuito** (sem assinatura, sem créditos), **local-first** e **BYO key**: o
> usuário usa a própria chave de IA (**OpenRouter, OpenAI ou Anthropic**) e todo o
> processamento de vídeo roda na máquina dele. Monetização futura ainda **não definida**
> — não há cobrança. Código **source-available** num único repo público (`Edualnog/medusa-cut`).

## Arquitetura-alvo

```text
SITE NEXT.JS (Vercel)  — estático
  landing pública 8-bit + download do app
  (SEM login, SEM api, SEM backend)
             │
             ▼
APP ELECTRON (PC do usuário)  — SEM CADASTRO
  abre direto (1º acesso → onboarding: aceite + pasta), sem login
  aceite legal gravado SÓ local (config.json: versão/data/itens)
  chave de IA protegida localmente (safeStorage, por provedor) → vai direto pro provedor
  motor Python + FFmpeg/FFprobe embutidos (binário)
  processamento e biblioteca 100% locais
```

Não há backend: sem conta, sem auth, sem Supabase. Nenhum dado de usuário nem arquivo
de gameplay sai do dispositivo. Os instaladores e o feed de auto-update são publicados
como GitHub Releases **neste mesmo repo público**, sem token no app.

## Estado em 20/06/2026

### Implementado

- motor Python completo: ingestão, sinais de áudio/movimento, seleção de candidatos,
  transcrição com timestamps, análise multimodal/multi-modelo via OpenRouter, reframe
  dinâmico + layouts + facecam, legenda karaokê, render H.264/AAC com FFmpeg;
- motor empacotado como **binário** + FFmpeg/FFprobe embutidos (self-contained, sem
  Python no sistema);
- app Electron: UI 8-bit (Início/Biblioteca/Chaves/Ajustes), geração, progresso,
  biblioteca local, custo acumulado;
- **sem cadastro (no sign-up)**: login/conta Supabase **removidos** do app e da web
  (em 21/06); o app abre direto no onboarding/app;
- onboarding de 1º acesso: aceites legais (Termos/Privacidade/conteúdo/18+) + escolha
  da pasta de clips; prova de aceite gravada **só localmente** (`config.json`);
- segurança: chave de IA (por provedor) **cifrada** no disco via `safeStorage`
  (migra config antigo em texto puro; fallback Linux sem keyring);
- landing 8-bit em Next.js (estática) refocada no app desktop + links de download;
- **CI de release single-repo**: matriz GitHub Actions builda macOS arm64 + Windows x64
  + Linux x86_64 nativamente e publica a Release neste repo via `GITHUB_TOKEN`;
- auto-update via `electron-updater` lendo o feed público (sem token no app);
- testes unitários do motor passando.

### Parcial ou pendente

- **assinatura/notarização de código**: builds não assinados (mac `identity:null`,
  Windows sem cert) → avisos de Gatekeeper/SmartScreen; no macOS sem assinatura o
  auto-update não troca o binário (só avisa e manda baixar no site);
- **decommission do Supabase: FEITO (2026-06-21)** — projeto deletado (banco + tabela
  `legal_acceptances` + auth), invalidando a anon key + service_role que estavam no repo;
- rotação dos segredos cloud antigos (R2) e revisão jurídica dos textos legais (pendente);
- faltam testes end-to-end do app empacotado e do render real.

## Motor de cortes — qualidade & velocidade (rodada 2026-06-20)

Foco: deixar os cortes "nível Opus Clip" e o processo mais rápido (LLM onde mais
importa, sem sacrificar qualidade). Validado no material real (gameplay GTA RP).

### Feito
- ~~**Reframe ciente de cena** (`reframe/composition.py`, `scene_layout.py`)~~ →
  **SUPERADO/REMOVIDO em 06-21**: era lento (chamada de IA por cena + optical-flow) e
  deixava barras pretas. Trocado pelos 2 layouts simples (ver rodada 06-21). Os módulos
  `composition.py`/`scene_layout.py`/`facecam_vlm.py` foram apagados.
- **Juiz multimodal consertado** (`pipeline.py`): era chamado com assinatura errada →
  `TypeError` engolido → o juiz (coração da seleção) NUNCA rodava; caía na triagem
  barata. Voltou a re-ranquear/refinar/dar gancho com arco.
- **Seleção por roteiro** (`hooks/propose.py`): transcreve o vídeo 1× e o LLM lê o
  transcript inteiro e PROPÕE janelas (arco narrativo) que a energia perde; funde com
  as de energia (`_merge_pool`). `WHISPER_MODEL=base` no `local.py` (transcrever tudo
  com `small` seria lento demais no PC).
- **Pular intro/patrocínio**: proposer e juiz começam no conteúdo real (não em
  vinheta/anúncio/divulgação).
- **Facecam headroom** (`compose._squarify_cam_box`): box não corta mais queixo/topo.
- **Performance ~32% (neutra em qualidade)**: gblur em bg reduzido, scene-detect com
  downscale+frame_skip, VLM por cena em paralelo, **facecam em 1 passada** de ffmpeg.
  Resultado: vídeo de 21min/3 cortes ~19min → ~8,5min. ~94 testes no motor.

### Próximos passos
1. Facecam letterboxed (barras borradas nas laterais) — avaliar preencher melhor ou
   ajustar proporção band facecam vs gameplay.
2. Duração por tipo de momento (clutch rápido vs RP longo) — hoje trilho único 60–180s.
3. Velocidade extra SÓ se aceitar trade de qualidade: HW-encode (videotoolbox no Mac) e
   render de clipes em paralelo; 30fps (~14%, não recomendado).
4. `fusion.MAX_LEN 300→180` (só CLI; desktop já passa 180).
5. Validar no app Electron ponta a ponta em hardware típico.
6. Tunar limiares de seleção (`TRIAGE_TEXT_W`/`SIGNAL_W`, count do proposer, calibração
   de virality) com mais vídeos.

## Motor & app — simplificação + performance (rodada 2026-06-21)

> Esta rodada **substituiu** boa parte do reframe da rodada 06-20 (o scene-aware/VLM
> por cena + optical-flow foram **removidos** — eram lentos e complexos). Foco: rápido
> de verdade + 2 layouts limpos. Resultado: **~25min → ~3-5min** num vídeo de 12min.

### Feito
- **Multi-provedor de IA (BYO key)**: OpenRouter, OpenAI e Anthropic. Seletor na aba
  Chaves; chave cifrada por provedor; `LLM_PROVIDER`+`LLM_API_KEY` no motor (OpenAI-compat
  vs SDK nativo Anthropic).
- **Download h264 ≤1080p** (`ingest/youtube.py`): o YouTube servia AV1 1440p, que o
  ffmpeg embutido decodifica lentíssimo — era o gargalo de ~25min.
- **Transcrição com GPU**: MLX (Mac Apple Silicon, ~3×) / CUDA (Win/Linux NVIDIA quando
  há libs) / faster-whisper CPU — auto + fallback seguro. `base`+greedy.
- **2 layouts só** (`reframe/compose.py`): A facecam-terço-superior+blur (model 1) / B
  gameplay tela cheia+blur. Facecam detectado por YuNet **só nos cantos superiores**.
  Removidos `scene_layout`/`composition`/`facecam_vlm` (código morto).
- **Legenda + hook num só encode**: faixa alpha (qtrle) + overlay único, fundido no
  render (era 2 encodes). **Hook** (manchete) queimado nos primeiros ~5s. Corrigido o
  bug da legenda sumir em cortes longos (estourava o nº de inputs do ffmpeg).
- **Paralelismo**: IA viral (`MEDUSA_LLM_WORKERS`) e render dos cortes (`MEDUSA_RENDER_WORKERS`).
- **App**: player do clipe DENTRO do app + preview no hover (URL por id `zclip://clip/<id>`,
  consertou o playback) + ordenação da biblioteca + score colorido por faixa + progresso
  animado + ícone GitHub + "baixar e instalar" no Mac (baixa+abre o .dmg).

### Pendente
- **GPU no Windows "de fábrica" (NVIDIA)**: o código usa CUDA se as libs existirem, mas
  entregar cuDNN sem o usuário instalar nada esbarra em licença NVIDIA + falta de wheel
  Windows + **necessita máquina Windows+NVIDIA pra validar** (CI não tem GPU).
- Assinatura/notarização (destrava auto-update silencioso no Mac + tira Gatekeeper/SmartScreen).

## Etapa A — Estabilização do processamento local

Objetivo: tornar o fluxo confiável antes da distribuição ampla.

- revisar o layout com auto-detecção de facecam (cair em `gameplay_blur` quando não há
  rosto, nunca faixa vazia);
- cancelamento de geração e recuperação após falha;
- validar espaço em disco, memória, arquitetura e codecs antes do job;
- melhorar mensagens de erro e logs de diagnóstico exportáveis;
- testar MP4, MOV, MKV e WebM em codecs e durações variados;
- testes de integração com pequenos fixtures de vídeo.

Critério: geração completa reproduzível sem dependências instaladas manualmente e sem
perda de resultados após reiniciar o app.

## Etapa B — Builds assinados multiplataforma

Objetivo: instaladores sem avisos de segurança do SO.

### macOS Apple Silicon (`arm64`)
- motor PyInstaller `arm64`, Electron e FFmpeg `arm64`, `.dmg`;
- **assinatura + notarização** (Apple Developer, US$99/ano) → destrava auto-update
  nativo e remove o Gatekeeper. (macOS Intel foi descontinuado — só Apple Silicon.)

### Windows (`x64`)
- motor PyInstaller `x64` (`.exe`), FFmpeg/FFprobe Windows, instalador NSIS;
- assinatura de código → remove o SmartScreen.

### Linux (`x64`)
- motor PyInstaller `x64`, FFmpeg/FFprobe compatíveis, `.AppImage` (principal) e `.deb`
  opcional; teste em Ubuntu LTS limpo.

O build acontece **nativamente** em cada SO/arquitetura — não é seguro depender de
cross-compilation para o stack Python/ML.

## Etapa C — CI, distribuição e atualização ✅

Objetivo: publicar versões sem processo manual frágil.

- [x] matriz de build no GitHub Actions (3 SOs nativos);
- [x] release única por tag `v*`, publicada neste repo via `GITHUB_TOKEN`
      (sem PAT cross-repo, sem secret);
- [x] `version` em `desktop/package.json` como fonte da verdade do updater;
- [x] feeds `latest*.yml` + instaladores como assets da Release;
- [ ] rodar testes/checks antes de gerar instaladores;
- [ ] checksums SHA-256 e notas de versão automáticas;
- [ ] canais estável e beta + rollback de versão.

## Etapa D — Operação e monetização (futura, indefinida)

O app é **gratuito** e a monetização ainda não foi decidida — **não** implementar
cobrança/assinatura. Quando houver modelo, ele não deve introduzir processamento cloud
de vídeo nem quebrar a privacidade local-first.

- estratégia: construir base grande de usuários primeiro, monetizar depois;
- telemetria técnica **opcional**, sem conteúdo de vídeo, com consentimento explícito;
- suporte a diagnóstico com consentimento;
- política de privacidade e termos publicados (revisão jurídica pendente).

## Ordem recomendada imediata

1. Etapa A: estabilizar o app local (facecam, cancelamento, codecs).
2. Etapa B: assinar/notarizar os builds quando houver conta Apple Developer.
3. Etapa C (restante): testes no CI, checksums, canais beta/rollback.
4. Etapa D: só quando/se o modelo de monetização for definido.
