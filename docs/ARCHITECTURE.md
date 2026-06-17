# Medusa Cut — Arquitetura (ferramenta pessoal)

> Tool pessoal e local. Um usuario, uma maquina, CLI. **Sem** SaaS, sem nuvem.

## Principio

Toda a complexidade de SaaS (auth, fila, workers, banco, storage, billing,
multi-tenant) existe por causa de "outras pessoas". Sendo so para o dono, nada
disso entra. O produto e o **motor + um CLI bom**, e o esforco vai pra qualidade.

## Fluxo

```
link YouTube
  → ingest (yt-dlp: video [+ chat replay se houver])
  → preprocess (ffmpeg: audio, fps, dimensoes)
  → transcribe (whisper: timestamps por palavra)   [sinal secundario]
  → sinais (audio_energy + scene_change [+ chat_velocity])
  → fusao (premia coincidencia) → top-N candidatos
  → GANCHO + score de viralizacao (LLM forte)       [define o nivel Opus Clip]
  → reframe/composicao 9:16 (facecam + acao)
  → render (ffmpeg) + legenda karaoke
  → out/clip_NN.mp4 + out/manifest.json
```

## Responsabilidade por modulo

| Modulo | Faz |
|---|---|
| `ingest/youtube` | baixa o video e, se for VOD de live, o chat replay |
| `transcribe` | texto + timestamps por palavra (p/ legenda e gancho) |
| `signals` | cada sinal vira uma trilha de score no tempo |
| `signals/fusion` | combina trilhas ponderadas → candidatos |
| `hooks` | gera gancho/titulo + score de viralizacao por candidato |
| `reframe` | detecta facecam, compoe layout 9:16 |
| `caption` | legenda karaoke queimada estilo gamer |
| `render` | montagem final via ffmpeg |
| `pipeline` | orquestra tudo; escreve out/ + manifest |

## Por que da pra chegar no nivel Opus Clip

Qualidade de short = gancho (retencao nos 2s) + legenda + enquadramento. Os tres
sao questao de craft (prompt, template, composicao), nao de infra. Em uso pessoal
da pra usar o melhor LLM sem pensar em custo por clipe — vantagem direta no gancho.

## Rodar (Apple Silicon)

ffmpeg via Homebrew; transcricao com faster-whisper, ou whisper.cpp/mlx-whisper
(mais rapido em Metal). Interface em `transcribe/` permite trocar a engine.

## Futuro opcional (so se incomodar)

- Mini UI local de revisao (Streamlit/Gradio ou um HTML unico) p/ ver thumbnails,
  hook e score e escolher cortes — em vez de abrir a pasta na mao.
- Presets de legenda por estilo de canal.
- `game_event` (OCR de HUD) por jogo, se quiser pescar kill/clutch automaticamente.
