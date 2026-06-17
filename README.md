# Medusa Cut

Ferramenta pessoal e local que transforma **link do YouTube** em **cortes 9:16 de
gameplay** com ganchos e legendas no nivel Opus Clip. Acha o momento por fusao de
sinais (audio, cena, chat) — nao por transcricao. CLI, roda na sua maquina.

> Status: scaffold. Interfaces prontas; implementacao em aberto. Ver `CLAUDE.md`.

## Comecar

```bash
git init
cp .env.example .env        # preencha o provedor de LLM + chave
make setup
make run URL="https://youtube.com/watch?v=..."
# cortes em out/ ; veja out/manifest.json (hook, score, reason por corte)
```

## Estrutura

```
src/medusacut/
  cli.py · pipeline.py · types.py
  ingest/      youtube (yt-dlp)
  transcribe/  whisper (timestamps por palavra)
  signals/     audio, cena, chat, fusao
  hooks/       gancho + score de viralizacao   ← coracao da qualidade
  reframe/     composicao 9:16 (facecam + acao)
  caption/     legenda karaoke
  render/      ffmpeg
docs/ARCHITECTURE.md
```
