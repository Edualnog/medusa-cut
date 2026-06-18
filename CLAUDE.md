# CLAUDE.md — Zorothax

Contexto para o Claude Code. Leia antes de codar.

> ⚠️ DIRECAO ATUAL (2026-06-17): SaaS **cloud**. O processamento roda num **worker
> na VPS do dono** (nao no PC do usuario, nao em agente baixavel). O usuario so cola
> a chave da OpenRouter e gera. O motor de cortes Python foi reaproveitado integral.

## O que e

**SaaS para criadores de games**: o usuario faz login, conecta a **propria** chave
da OpenRouter (numa aba), cola um link do YouTube e recebe **cortes verticais 9:16**
nivel Opus Clip (ganchos, legenda karaoke, enquadramento). Assinatura simples
(~R$11,90/mes), **sem creditos** — o custo de IA (LLM) e do usuario, pela chave dele.
Simplicidade total: **nada de baixar nada**, so colar a chave.

## Arquitetura: Vercel + Supabase + WORKER (VPS) — "Caminho A"

Processamento de video (yt-dlp, ffmpeg, whisper, render) e **pesado** — NAO roda em
serverless (Vercel). Roda num **worker** (container Docker) numa **VPS do dono**.

```
WEB (Next.js @ Vercel)            WORKER (Python @ VPS do dono, Docker)
  landing 8-bit + login            escuta a fila de jobs no Supabase
  aba "Chaves API"                 pega job -> baixa + corta + render
  cola link -> cria job            usa a chave do user (decifrada no server)
  biblioteca + progresso           sobe os clipes -> Storage; reporta progresso
        \                                   /
         \------------ SUPABASE ----------/
       (auth + Postgres + storage + realtime + fila de jobs = backend)
```

- **Vercel**: so o site (UI/auth/rotas leves). **VPS**: so o worker pesado.
  **Supabase**: banco + auth + storage + realtime (a "fila" e uma tabela `jobs`).
- **Custo de compute e do DONO** (VPS): banda + CPU + storage. Por isso provavel
  **limite de uso justo** no plano. (Antes, com agente local, era ~zero — mudou.)
- **Risco operacional**: baixar do YouTube de IP de datacenter (VPS) pode ser
  bloqueado/ferir ToS. Monitorar; mitigar com ritmo/cookies.

## Regras inegociaveis (seguranca + modelo)

- **BYO key**: cada usuario usa a PROPRIA chave da OpenRouter. **NUNCA** publicar a
  chave do dono nem rodar IA "as custas da casa". A chave do usuario fica no Supabase
  **cifrada (AES-256-GCM)** + RLS, **nunca** volta pro navegador (so os 4 ultimos
  digitos), e e usada **server-side** (worker) — nunca exposta no client.
- `service_role` e `KEY_ENCRYPTION_SECRET`: **so no servidor** (env Vercel/VPS),
  nunca `NEXT_PUBLIC`, nunca no git.
- **Sem creditos**: cobranca por assinatura; custo de IA e do usuario.
- **Multi-tenant**: RLS no Supabase em TODAS as tabelas — um usuario so ve o proprio.

## Onde mora a qualidade ("nivel Opus Clip")

No motor (`agent/src/medusacut/`), inalterado pela virada SaaS:

1. **Analise viral multimodal + multi-modelo** (`hooks/`, `frames.py`, `llm.py`):
   triagem barata (texto) -> juiz forte que VE keyframes -> re-rank.
2. **Legenda karaoke** (`caption/`): queimada, palavra a palavra, estilo gamer.
3. **Reframe** (`reframe/`): segue a acao (ciente de corte de cena), facecam
   auto-detectado, layouts (facecam-em-cima, fundo desfocado).

## Monorepo

```
agent/    # Python: motor de cortes (ex-`medusacut`). Vira o WORKER da VPS.
  src/medusacut/  cli.py · pipeline.py · types.py · llm.py · frames.py
                  ingest/ transcribe/ signals/ hooks/ reframe/ caption/ render/ ui/
  tests/  pyproject.toml  Makefile  docs/ARCHITECTURE.md
web/      # Next.js (App Router) @ Vercel: landing 8-bit, auth, painel, biblioteca
supabase/ # migrations (SQL), RLS, policies
docs/     # SETUP.md (guia de montagem da infra)
```

## Convencoes

**Agente/Worker (Python)**: Python 3.11+, type hints, `from __future__ import
annotations`. Deps pesadas (yt_dlp, faster_whisper, cv2, openai, PIL) importadas
DENTRO das funcoes. Teste por capacidade nova em `agent/tests/`. Versoes pinadas.

**Web (Next.js)**: TypeScript, App Router. Estilo **8-bit gamer**: fonte pixel
(Press Start 2P / VT323), fundo preto estrelado, bordas pixeladas. Segredo de
servidor SO em rotas `app/api/*` (runtime nodejs); nada sensivel no client.

**Geral**: `out/`, `.env`, `.env*.local`, video e `node_modules` NUNCA no git.
O dono conecta as contas (Supabase, Vercel, VPS); o Claude escreve o codigo e
**guia o dono passo a passo** no deploy (ver `docs/SETUP.md`).

## Status / roadmap

- [x] Motor de cortes completo (viral multimodal, legenda, reframe, custo).
- [x] Fase 1: landing 8-bit + shell web + login Supabase.
- [x] Fase 2: aba Chaves API (salvar chave OpenRouter cifrada, RLS).
- [ ] **Fase 3**: jobs (fila no Supabase) + WORKER na VPS (consumir/processar/subir).
- [ ] Fase 4: biblioteca de clipes + progresso realtime na web.
- [ ] Fase 5: assinatura (Stripe/Mercado Pago) + limite de uso justo.
- [ ] Fase 6: deploy completo (Vercel + VPS) e onboarding.

## Comandos

```bash
cd agent && make setup && make test          # motor de cortes
cd web && npm install && npm run dev          # site -> http://localhost:3000
```
