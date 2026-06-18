# Guia de montagem — Zorothax (SaaS)

Mapa pra subir tudo. Arquitetura **Caminho A**: Vercel (site) + Supabase (dados) +
VPS (worker). Você cria as contas e cola as chaves; eu (Claude) escrevo o código e
te guio em cada passo. Itens marcados ⏳ dependem da Fase 3 (worker) — chego neles.

## As 3 peças (e o que cada uma faz)

| Peça | Faz | Custo |
|---|---|---|
| **Vercel** | hospeda o **site** (landing, login, painel). Deploy com `git push`. | grátis pra começar |
| **Supabase** | **banco + login + storage + fila de jobs**. | grátis pra começar |
| **VPS** (Hostinger KVM) | roda o **worker** que baixa/corta/renderiza o vídeo. | ~R$44–60/mês |

Segredos por lugar (NUNCA no git):
- **Navegador (público)**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Servidor web (Vercel)**: `SUPABASE_SERVICE_ROLE_KEY`, `KEY_ENCRYPTION_SECRET`.
- **Worker (VPS)**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `KEY_ENCRYPTION_SECRET`
  (o mesmo da web, pra decifrar a chave do user).

---

## 1) Supabase (banco/auth)  — em andamento

1. Projeto criado em supabase.com ✅
2. **SQL Editor** → rode os arquivos de `supabase/migrations/` em ordem:
   - `0001_user_api_keys.sql` (chave de API do user, cifrada + RLS).
   - ⏳ `0002_jobs.sql` (fila de jobs + clipes) — vem na Fase 3.
3. **Authentication → Providers → Email**: pra testar rápido, desligue
   "Confirm email" (ou confirme pelo e-mail).
4. **Project Settings → API**: copie `Project URL`, `anon key` (públicas) e
   `service_role` (SECRETA — só no servidor).

## 2) Site (Next.js)

**Local (agora):** `web/.env.local` com as 4 variáveis (as 2 públicas + as 2 de
servidor). Rode `cd web && npm run dev`.

**Deploy na Vercel (quando quiser publicar):**
1. Conecte o repositório na vercel.com, root = `web/`.
2. Em **Settings → Environment Variables**, cole as MESMAS 4 variáveis.
3. Deploy. (HTTPS e CDN automáticos.)
4. **Domínio `zorothax.com`**: Vercel → Settings → Domains → adicionar o
   domínio; a Vercel te dá os registros DNS (um `A`/`CNAME`) pra colar no painel do
   teu registrador. HTTPS sai automático.

## 3) VPS — o worker  (Fase 3)

O `agent/Dockerfile` + `docker-compose.yml` já existem. Passo a passo na VPS Ubuntu:

```bash
# 1. acessar (Hostinger te dá o IP + senha root)
ssh root@SEU_IP

# 2. instalar Docker
curl -fsSL https://get.docker.com | sh

# 3. colocar o código na VPS (escolha um):
#    (a) Git (melhor p/ atualizar depois): repo no GitHub -> git clone <url>
#    (b) rápido, do seu Mac:  rsync -av --exclude .venv --exclude out agent/ root@SEU_IP:/root/medusacut/
cd /root/medusacut          # (ou medusa-cut/agent, conforme o clone)

# 4. criar o .env do worker (cole os MESMOS 3 valores do web/.env.local)
cat > .env <<'ENV'
SUPABASE_URL=https://xukvtvggqdirvbrqqdjw.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<cole>
KEY_ENCRYPTION_SECRET=<cole o mesmo do web>
ENV

# 5. subir (a 1ª build demora alguns min: instala ffmpeg + stack de ML)
docker compose up -d --build

# 6. ver os logs — deve aparecer "conectado ao Supabase; escutando a fila…"
docker compose logs -f
```

Atualizar depois: `git pull` (ou rsync de novo) + `docker compose up -d --build`.

**Notas:** 1 job por vez (KVM 2) / ~2 (KVM 4). No 1º job o whisper baixa o modelo
(fica em volume, não rebaixa). Temporários são limpos a cada job; só o clipe final
vai pro Storage.

---

## Ordem recomendada

1. Supabase: rodar `0001` + pegar as chaves. ✅ (você faz isso agora)
2. Web local funcionando (salvar a chave da OpenRouter na aba Chaves API).
3. **Fase 3** (eu codo): jobs + worker. Aí montamos a VPS juntos.
4. Fase 4: biblioteca + progresso. Fase 5: assinatura. Fase 6: deploy final.

> Resumo da segurança: a chave da OpenRouter do usuário fica **cifrada (AES-256)**
> no Supabase, com RLS negando acesso direto; só o servidor (web e worker, com o
> `service_role` + `KEY_ENCRYPTION_SECRET`) decifra. O navegador nunca vê o valor.
