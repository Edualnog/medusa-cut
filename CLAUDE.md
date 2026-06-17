# CLAUDE.md — Medusa Cut

Contexto para o Claude Code. Leia antes de codar.

## O que e

**Ferramenta PESSOAL e LOCAL** (um unico usuario: o dono) que recebe um **link do
YouTube** e gera **cortes verticais 9:16 de gameplay** com qualidade nivel Opus
Clip — bons ganchos, boas legendas, bom enquadramento. Roda via CLI, escreve os
cortes numa pasta. Sem nuvem, sem contas, sem cobranca.

## O que ISTO NAO E (nao construa)

Nao e SaaS. **Nao adicione** API web, frontend, fila, workers, banco de dados,
auth, billing, storage em nuvem, multi-usuario, nem modelo de creators. Se a
vontade de "preparar pra escalar" aparecer, ignore — o objetivo e uma ferramenta
afiada pra uma pessoa so.

## Onde mora a qualidade ("nivel Opus Clip")

Num tool pessoal, qualidade nao vem de infra — vem de tres alavancas. Gaste a
energia AQUI:

1. **Gancho + score** (`hooks/`): LLM forte sobre o trecho transcrito gera o
   titulo/hook e pontua viralizacao. Maior fator de retencao. Custo de LLM e
   irrelevante em uso pessoal — use o melhor modelo.
2. **Legenda karaoke** (`caption/`): legenda queimada estilo gamer, palavra a
   palavra. Metade da performance de um short.
3. **Reframe/composicao** (`reframe/`): facecam + acao compostos em 9:16.

A selecao de momento e por **fusao de sinais** (audio + cena [+ chat se houver]),
nao por transcricao — e onde os concorrentes falham em gameplay. Transcricao
serve p/ legenda e p/ alimentar o gancho, nao p/ achar o corte.

## Arquitetura (simples de proposito)

Um pacote Python `medusacut` rodado por CLI. Fluxo sincrono, um video por vez:

```
link YouTube → ingest (yt-dlp) → preprocess (ffmpeg) → transcribe (whisper)
  → sinais → fusao → top-N → GANCHO+score → reframe → render+legenda
  → out/clip_NN.mp4 + out/manifest.json
```

O `manifest.json` lista hook, score, reason e arquivo de cada corte, pra voce
abrir a pasta e escolher os melhores.

## Rodar local (Apple Silicon)

- `ffmpeg` via Homebrew (`brew install ffmpeg`).
- Transcricao: `faster-whisper` funciona; em Apple Silicon, `whisper.cpp` (Metal)
  ou `mlx-whisper` sao mais rapidos. A interface em `transcribe/` permite trocar
  sem mexer no pipeline.
- Ganchos via API de LLM na nuvem (chave no `.env`).

## Ordem de implementacao

Meta: corte BOM saindo de um link real. Fatias verticais, uma de cada vez:

1. `ingest/youtube.py` (yt-dlp baixa video) + preprocess (ffmpeg).
2. `signals/audio_energy.py` + `signals/fusion.py` → candidatos.
3. `reframe/layouts.py::GameplayOnly` + `render/ffmpeg.py` → **primeiro corte
   ponta a ponta** (mesmo cru). Marco que destrava tudo.
4. `transcribe/` (whisper, timestamps) + `caption/` (legenda karaoke).
5. `hooks/base.py` (gancho + score) → ordenar candidatos por viralizacao.
6. `signals/scene_change.py`, depois `reframe/facecam.py` + layout com facecam.
7. Opcionais: `signals/chat_velocity.py` (chat replay YouTube), `game_event`.

## Convencoes

- Python 3.11+, type hints, `from __future__ import annotations`.
- Deps pesadas (yt_dlp, whisper, ffmpeg) importadas DENTRO de funcoes, nunca no
  topo de modulo — mantem `import medusacut` leve.
- Cada capacidade nova vem com teste em `tests/`.
- Pin de versoes no install (stack de ML e fragil).
- `out/`, `.env` e arquivos de video NUNCA entram no git.

## Comandos

```bash
make setup
make run URL="https://youtube.com/watch?v=..."
make test
```
