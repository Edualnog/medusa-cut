# Roadmap técnico — Medusa Clip local-first

## Arquitetura-alvo

```text
SITE NEXT.JS
  landing pública
  autenticação Supabase
  conta/assinatura e download autorizado
             │
             ▼
SUPABASE
  Authentication
  Postgres com dados mínimos de usuário e entitlement
             │
             ▼
APP ELECTRON
  login e validação de acesso
  chave OpenRouter protegida localmente
  motor Python + FFmpeg/FFprobe embutidos
  processamento e biblioteca 100% locais
```

Supabase continua sendo infraestrutura do SaaS, mas não participa do pipeline de
vídeo. Nenhum arquivo de gameplay precisa passar pelo backend do produto.

## Estado em 18/06/2026

### Implementado

- motor Python com ingestão, sinais de áudio/movimento e seleção de candidatos;
- transcrição com timestamps e análise multimodal via OpenRouter;
- reframe dinâmico, layouts, facecam e legenda karaokê;
- renderização H.264/AAC com FFmpeg;
- Electron com geração, progresso, biblioteca e custo acumulado;
- empacotamento inicial para macOS com PyInstaller e electron-builder;
- landing e identidade visual em Next.js;
- autenticação Supabase implementada no protótipo web;
- 49 testes unitários do motor passando.

### Parcial ou legado

- web ainda contém painel, R2 e APIs de processamento cloud do protótipo anterior;
- worker de VPS e migrations Supabase permanecem no repositório como legado;
- chave OpenRouter do desktop ainda é salva em arquivo local sem cofre do sistema;
- build web passa após a remoção da página experimental `/spike` e de `mp4box`;
- auto-detecção de facecam não é acionada no fluxo padrão por uma inconsistência
  na resolução do layout;
- não existem testes end-to-end do aplicativo empacotado ou do render real.

## Etapa 1 — Reposicionamento da web

Objetivo: transformar `web/` em site de aquisição e distribuição.

- manter landing, branding, preço, FAQ e documentação de requisitos;
- remover da navegação pública o painel de geração e a biblioteca cloud;
- manter Supabase Auth e adaptar o fluxo para aquisição/download;
- definir uma área mínima de conta para sessão, assinatura e downloads;
- remover dependências cloud não utilizadas do bundle web;
- manter `supabase/migrations/` no repositório, sem executar novas migrations;
- corrigir o build e adicionar validação em CI.

Critério de conclusão: visitante cria conta, autentica e chega ao download correto
para seu sistema, sem qualquer rota de processamento de vídeo na web.

## Etapa 2 — Identidade e acesso com Supabase

Objetivo: compartilhar a identidade do usuário entre site e aplicativo.

- configurar projetos Supabase separados para desenvolvimento e produção;
- habilitar provedores de autenticação definidos pelo produto;
- modelar usuário, plano, status da assinatura e entitlement no Postgres com RLS;
- implementar login no site e no Electron;
- validar os JWTs do Supabase em operações privilegiadas;
- guardar sessão e chave OpenRouter com o cofre nativo do sistema operacional;
- definir comportamento offline e período de tolerância da licença.

Decisão pendente: login por e-mail/senha, Google ou ambos.

## Etapa 3 — Estabilização do processamento local

Objetivo: tornar o fluxo atual confiável antes da distribuição ampla.

- corrigir o layout com auto-detecção de facecam;
- adicionar cancelamento de geração e recuperação após falha;
- validar espaço em disco, memória, arquitetura e codecs antes do job;
- melhorar mensagens de erro e logs de diagnóstico exportáveis;
- proteger a chave OpenRouter com Keychain, Credential Manager e Secret Service;
- testar vídeos MP4, MOV, MKV e WebM em diferentes codecs e durações;
- criar testes de integração com pequenos fixtures de vídeo.

Critério de conclusão: geração completa reproduzível no macOS sem dependências
instaladas manualmente e sem perda dos resultados após reiniciar o app.

## Etapa 4 — Builds multiplataforma

Objetivo: produzir quatro artefatos independentes e reproduzíveis.

### macOS Apple Silicon

- motor PyInstaller `arm64`;
- Electron e FFmpeg `arm64`;
- `.dmg` assinado e notarizado.

### macOS Intel

- motor PyInstaller `x64`;
- Electron e FFmpeg `x64`;
- `.dmg` assinado e notarizado.

### Windows

- motor PyInstaller `x64` com executável `.exe`;
- FFmpeg/FFprobe para Windows e ajustes de caminhos;
- instalador NSIS assinado.

### Linux

- motor PyInstaller `x64`;
- FFmpeg/FFprobe compatíveis com a distribuição-base;
- `.AppImage` como formato principal e `.deb` opcional;
- teste em Ubuntu LTS limpo.

O build deve acontecer nativamente em cada sistema/arquitetura. Não é seguro
depender de cross-compilation para o stack Python/ML atual.

## Etapa 5 — CI, distribuição e atualização

Objetivo: publicar versões sem processo manual frágil.

- criar matriz de build no GitHub Actions;
- executar testes e checks antes de gerar instaladores;
- versionar app, motor e formato do manifest em conjunto;
- gerar checksums SHA-256 e notas de versão;
- enviar artefatos para armazenamento de releases com acesso integrado ao Supabase;
- entregar URLs temporárias conforme autenticação/entitlement;
- configurar atualização automática por canal estável e beta;
- implementar rollback para uma versão anterior.

Recomendação: não usar releases de um repositório privado como URL direta no app,
pois isso exigiria distribuir um token do GitHub. Usar armazenamento próprio com
feed HTTPS assinado é mais seguro.

## Etapa 6 — Pagamentos e operação

Objetivo: fechar o ciclo SaaS sem introduzir processamento cloud de vídeo.

- integrar o provedor de pagamento;
- atualizar entitlement por webhook idempotente;
- implementar cancelamento, renovação e período de tolerância;
- publicar política de privacidade e termos de uso;
- coletar apenas telemetria técnica opcional e sem conteúdo dos vídeos;
- criar suporte a diagnóstico com consentimento explícito.

## Ordem recomendada imediata

1. Etapa 1: simplificar a web e corrigir o build.
2. Etapa 2: adaptar Supabase Auth e implementar entitlement.
3. Etapa 3: estabilizar o app local no macOS Apple Silicon.
4. Etapas 4 e 5: expandir builds e distribuição.
5. Etapa 6: conectar pagamento quando o download autenticado estiver estável.
