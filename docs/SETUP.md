# Guia de montagem — Medusa Clip

Mapa pra subir tudo. Arquitetura **local-first, sem cadastro**: o app desktop faz todo
o trabalho no PC do usuário e **não há backend**. A única peça de nuvem é a **Vercel**,
que hospeda o site estático (landing + downloads). Sem Supabase, sem login, sem VPS,
sem worker.

## As peças (e o que cada uma faz)

| Peça | Faz | Custo |
|---|---|---|
| **App desktop** (Electron) | baixa/corta/renderiza o vídeo **no PC do usuário**; guarda config + aceite legal localmente. | grátis (compute é do usuário) |
| **Vercel** | hospeda o **site estático** (landing + downloads). Deploy com `git push`. | grátis |
| **GitHub Releases** | distribui os instaladores + feeds de auto-update. | grátis |

Não há segredos de servidor: a chave de IA fica **cifrada no DISPOSITIVO do usuário**
(`safeStorage` — Keychain/DPAPI/libsecret), **nunca** sai pra nenhum servidor, e vai
direto pro provedor escolhido.

---

## 1) Site (Next.js @ Vercel)

**Local:** `cd web && npm install && npm run dev` → http://localhost:3000. Sem
`.env` obrigatório (site estático, sem variáveis de ambiente).

**Deploy na Vercel:**
1. Conecte o repositório na vercel.com, **Root Directory = `web/`**.
2. **Sem Environment Variables** a cadastrar (não há login/api/Supabase).
3. Deploy. (HTTPS e CDN automáticos.)
4. **Domínio `medusaclip.com`**: Vercel → Settings → Domains → adicionar o domínio; a
   Vercel te dá os registros DNS (`A`/`CNAME`) pra colar no painel do registrador.

## 2) App desktop

Sem cadastro: ao abrir pela 1ª vez, o usuário passa pelo onboarding (aceite dos termos
+ escolha da pasta dos clips) e conecta a chave de IA (OpenRouter/OpenAI/Anthropic) na
aba **Chaves API**. Nada disso sai do dispositivo.

### Rodar localmente a partir do código (dev)

Roda o app exatamente como em produção, na sua máquina (sem instalar nada de nuvem).

**Pré-requisitos:**
- **Git**
- **Node.js 18+** (LTS) — vem com o `npm`
- **Python 3.11** — o motor de cortes é Python empacotado num binário; a stack de ML
  (faster-whisper/ctranslate2) nem sempre tem wheels pras versões mais novas, por isso 3.11
- macOS/Windows/Linux: o `ffmpeg`/`ffprobe` vêm pelo `npm` (não precisa instalar à parte)

**Passo a passo:**
```bash
# 1. baixe o código
git clone https://github.com/Edualnog/medusa-clip.git
cd medusa-clip/desktop

# 2. dependências do app (Electron + ffmpeg/ffprobe)
npm install

# 3. prepara o MOTOR (Python -> binário) dentro de desktop/engine/
#    demora alguns minutos na 1ª vez (baixa a stack de ML e empacota com PyInstaller)
npm run engine
#    obs.: usa python3.11 por padrão; pra outro interpretador: PYTHON=python3.12 npm run engine

# 4. abre o app
npm start
```

O app abre na tela de onboarding (sem cadastro). Conecte sua chave de IA na aba
**Chaves API**, escolha um vídeo/link e gere os cortes — tudo local.

**Ciclo de desenvolvimento (o que recompilar ao mexer):**
- Mexeu em `desktop/renderer/` ou `desktop/main.js` (interface/app) → **feche e rode `npm start`** de novo.
- Mexeu no motor `agent/` (Python) → rode **`npm run engine`** de novo (re-empacota o binário) e depois `npm start`.

> A pasta `desktop/engine/` (o binário + ffmpeg) **não vai pro git** — por isso o passo 3
> é obrigatório num clone novo; sem ele o `npm start` abre, mas não consegue gerar cortes.

### (Opcional) rodar só o motor pela linha de comando
```bash
cd agent && make setup && make test
.venv/bin/medusacut "https://youtube.com/watch?v=..." --out out --clips 3
```

---

## Distribuição + auto-update (app desktop)

> Builds **não-assinados** por enquanto (decisão atual): instalam com botão-direito →
> Abrir (Mac) / "mais informações → executar assim mesmo" (Windows). Assinatura/
> notarização entram quando houver conta Apple Developer — aí o auto-update do Mac
> liga 100%.

### Arquitetura: um único repo PÚBLICO open source (código + releases)
- Código-fonte **e** releases: `Edualnog/medusa-clip` (**público, open source AGPL-3.0**;
  ver `LICENSE`).
- Os 3 lugares apontam pra cá: `desktop/package.json` (`build.publish`),
  `desktop/main.js` (`GITHUB_REPO`), `web/app/page.tsx` (`RELEASE_REPO`).

### 1. Sem pré-requisito de token
- A release sai **neste mesmo repo** via `GITHUB_TOKEN` nativo (o job `release` tem
  `permissions: contents: write`). **Não** precisa de PAT nem do secret `RELEASES_TOKEN`.

### 2. Publicar uma versão
- Subir `desktop/package.json` `version` (ex.: `0.1.8`) — é a **fonte da verdade** do updater.
- `git tag v0.1.8 && git push --tags` → o workflow `.github/workflows/release.yml` builda
  **macOS Apple Silicon (arm64)**, **Windows (x64)** e **Linux (x86_64)** nativamente e
  publica os instaladores + os feeds (`latest*.yml`) na Release deste repo.
  (macOS Intel foi descontinuado a pedido do dono — só Apple Silicon.)

### 3. Como o usuário atualiza
- **Windows/Linux**: ao abrir, o app checa a Release; se houver versão maior, mostra
  "NOVA VERSÃO vX — BAIXAR" → baixa → "REINICIE PRA INSTALAR" → reinicia já atualizado.
- **macOS (sem assinatura)**: o app **avisa** e manda **baixar no site** (não troca o
  binário sozinho — limitação do macOS p/ apps não assinados). Vira troca in-app quando assinar.
- Os botões de download da web apontam pra `releases/latest/download/MedusaClip-<os>-<arch>.<ext>`
  (nomes fixos via `artifactName` no electron-builder) — sempre a última versão.

### Build local (sem CI), no próprio SO
```bash
cd desktop && PYTHON=python3.11 bash scripts/build_app.sh   # -> desktop/dist/
```
