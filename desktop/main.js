// Processo principal do Electron: janela, chave, dispara o BINARIO do motor
// (medusacut-engine), repassa o progresso (JSON), e serve a biblioteca local.

const { app, BrowserWindow, ipcMain, dialog, shell, protocol, net, safeStorage } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const readline = require("readline");
const { pathToFileURL } = require("url");

let win = null;
let child = null;

const configPath = () => path.join(app.getPath("userData"), "config.json");
function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath(), "utf8"));
  } catch {
    return {};
  }
}
function saveConfig(c) {
  fs.writeFileSync(configPath(), JSON.stringify(c));
}

// --- Cifragem de segredos no disco (chave OpenRouter, tokens de sessao).
// Usa o cofre do SO via safeStorage (Keychain no macOS, DPAPI no Windows,
// libsecret no Linux). Onde nao ha cofre (Linux sem keyring), cai pra texto
// puro marcado, pra nao travar o app — limitacao conhecida.
function secretsEncrypted() {
  try {
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

// Retorna { v: "enc"|"plain", d: <base64|texto> } pra sabermos como decifrar depois.
function encryptSecret(plain) {
  if (plain == null) return null;
  if (secretsEncrypted()) {
    return { v: "enc", d: safeStorage.encryptString(String(plain)).toString("base64") };
  }
  return { v: "plain", d: String(plain) };
}

function decryptSecret(box) {
  if (!box) return "";
  try {
    if (box.v === "enc") return safeStorage.decryptString(Buffer.from(box.d, "base64"));
    return box.d || "";
  } catch {
    return "";
  }
}

// Migra config antigo (chave/sessao em texto puro) pro formato cifrado. Idempotente.
function migrateConfig() {
  const c = loadConfig();
  let changed = false;

  if (typeof c.key === "string") {
    if (c.key) c.keyEnc = encryptSecret(c.key);
    delete c.key;
    changed = true;
  }
  // sessao antiga: { access_token, refresh_token, expires_at, email } em claro
  if (c.session && typeof c.session === "object" && c.session.access_token) {
    c.sessionEnc = {
      email: c.session.email || null,
      expires_at: c.session.expires_at || null,
      access: encryptSecret(c.session.access_token),
      refresh: encryptSecret(c.session.refresh_token),
    };
    delete c.session;
    changed = true;
  }

  c.secretsPlaintext = !secretsEncrypted();
  if (changed) saveConfig(c);
}

// --- Auth (Supabase). A anon key e publica por design (protegida por RLS no banco).
const SUPABASE_URL = process.env.MEDUSA_SUPABASE_URL || "https://xukvtvggqdirvbrqqdjw.supabase.co";
const SUPABASE_ANON_KEY =
  process.env.MEDUSA_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a3Z0dmdncWRpcnZicnFxZGp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MzU0OTcsImV4cCI6MjA5NzMxMTQ5N30.DfXNTgf08l782ZJxDajsRnF0_Za63eovmdZJFxkMS_o";

async function supabaseAuth(endpoint, body) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY,
      Authorization: "Bearer " + SUPABASE_ANON_KEY,
    },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  return { status: r.status, data };
}

function authError(data, fallback) {
  return data.error_description || data.msg || data.message || data.error || fallback;
}

// Backend do site (rotas privilegiadas, ex.: exclusao de conta). Dev: aponte pro
// localhost com MEDUSA_API_BASE=http://localhost:3000.
const API_BASE = process.env.MEDUSA_API_BASE || "https://medusaclip.com";

// Access token valido: renova com o refresh_token se ja expirou.
async function getValidAccessToken() {
  const s = loadConfig().sessionEnc;
  if (!s) return null;
  const access = decryptSecret(s.access);
  if (s.expires_at && s.expires_at * 1000 > Date.now() + 60_000) return access || null;
  const refresh = decryptSecret(s.refresh);
  if (!refresh) return access || null;
  try {
    const { status, data } = await supabaseAuth("token?grant_type=refresh_token", {
      refresh_token: refresh,
    });
    if (status === 200 && data.access_token) {
      storeSession(data);
      return data.access_token;
    }
  } catch {
    return access || null;
  }
  return access || null;
}

// Guarda a sessao no config local: tokens CIFRADOS; email/expiry em claro (nao
// sensiveis, usados pra decidir renovacao sem precisar decifrar).
function storeSession(sess) {
  const c = loadConfig();
  c.sessionEnc = sess
    ? {
        email: (sess.user && sess.user.email) || null,
        expires_at: sess.expires_at || null,
        access: encryptSecret(sess.access_token),
        refresh: encryptSecret(sess.refresh_token),
      }
    : null;
  saveConfig(c);
}

function enginePath() {
  if (process.env.ENGINE_BIN) return process.env.ENGINE_BIN;
  if (app.isPackaged) return path.join(process.resourcesPath, "engine", "medusacut-engine");
  return path.join(__dirname, "engine", "medusacut-engine"); // dev: engine/ montada
}
// ffmpeg/ffprobe vivem na mesma pasta do motor -> entram no PATH do subprocesso
function engineEnv() {
  const dir = path.dirname(enginePath());
  return { ...process.env, PATH: dir + path.delimiter + (process.env.PATH || "") };
}

function defaultLibraryDir() {
  return path.join(app.getPath("downloads"), "Medusa Clip");
}

// Pasta onde os clips sao salvos: a escolhida no onboarding, ou a padrao.
function libraryRoot() {
  const dir = loadConfig().libraryDir || defaultLibraryDir();
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function youtubeVideoId(rawUrl) {
  let parsed;
  try {
    parsed = new URL(String(rawUrl || "").trim());
  } catch {
    return null;
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) return null;
  const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
  let videoId = null;

  if (host === "youtu.be") {
    videoId = parsed.pathname.split("/").filter(Boolean)[0];
  } else if (["youtube.com", "m.youtube.com", "music.youtube.com"].includes(host)) {
    if (parsed.pathname === "/watch") videoId = parsed.searchParams.get("v");
    else {
      const parts = parsed.pathname.split("/").filter(Boolean);
      if (["shorts", "live", "embed"].includes(parts[0])) videoId = parts[1];
    }
  }

  return /^[a-zA-Z0-9_-]{11}$/.test(videoId || "") ? videoId : null;
}

function isYoutubeUrl(rawUrl) {
  try {
    const parsed = new URL(String(rawUrl || "").trim());
    const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
    return ["youtu.be", "youtube.com", "m.youtube.com", "music.youtube.com"].includes(host);
  } catch {
    return false;
  }
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function thumbnailDataUrl(rawUrl) {
  if (!rawUrl) return null;
  const parsed = new URL(rawUrl);
  const host = parsed.hostname.toLowerCase();
  if (parsed.protocol !== "https:" || !(host === "ytimg.com" || host.endsWith(".ytimg.com"))) return null;

  const response = await fetchWithTimeout(parsed.toString());
  if (!response.ok) return null;
  const contentType = (response.headers.get("content-type") || "").split(";")[0];
  if (!contentType.startsWith("image/")) return null;
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length > 1_500_000) return null;
  return `data:${contentType};base64,${bytes.toString("base64")}`;
}

// esquema privilegiado pra tocar os clipes locais no <video> (CSP-safe)
protocol.registerSchemesAsPrivileged([
  { scheme: "zclip", privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true } },
]);

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 700,
    backgroundColor: "#060608",
    title: "Medusa Clip",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile(path.join(__dirname, "renderer", "index.html"));
}

app.whenReady().then(() => {
  migrateConfig(); // safeStorage so fica disponivel apos o ready
  // zclip://abs/<caminho-do-arquivo> -> serve o arquivo de video local
  protocol.handle("zclip", (request) => {
    const p = decodeURIComponent(request.url.replace(/^zclip:\/\//, ""));
    return net.fetch(pathToFileURL(p).toString());
  });
  createWindow();
});
app.on("window-all-closed", () => app.quit());
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.handle("pick-file", async () => {
  const r = await dialog.showOpenDialog(win, {
    properties: ["openFile"],
    filters: [{ name: "Vídeo", extensions: ["mp4", "mov", "mkv", "webm"] }],
  });
  return r.canceled ? null : r.filePaths[0];
});
ipcMain.handle("auth-sign-in", async (_e, { email, password } = {}) => {
  try {
    const { status, data } = await supabaseAuth("token?grant_type=password", { email, password });
    if (status === 200 && data.access_token) {
      storeSession(data);
      return { ok: true, email: data.user && data.user.email };
    }
    return { ok: false, error: authError(data, "Não foi possível entrar.") };
  } catch {
    return { ok: false, error: "Sem internet ou Supabase fora do ar." };
  }
});

ipcMain.handle("auth-sign-up", async (_e, { email, password } = {}) => {
  try {
    const { status, data } = await supabaseAuth("signup", { email, password });
    if (status === 200 && data.access_token) {
      storeSession(data);
      return { ok: true, email: data.user && data.user.email };
    }
    // Conta criada mas o projeto exige confirmacao por e-mail.
    if (status === 200) return { ok: true, needsConfirm: true };
    return { ok: false, error: authError(data, "Não foi possível criar a conta.") };
  } catch {
    return { ok: false, error: "Sem internet ou Supabase fora do ar." };
  }
});

ipcMain.handle("auth-sign-out", () => {
  storeSession(null);
  return true;
});

// Email do usuario logado (pra exibir na aba CONTA).
ipcMain.handle("get-account", () => {
  const s = loadConfig().sessionEnc;
  return { email: (s && s.email) || null };
});

// Dispara o email de recuperacao de senha. Serve aos dois casos:
//  - "esqueci a senha" (deslogado): email vem da tela de login;
//  - "trocar senha" (logado): cai no email da sessao.
// A redefinicao em si finaliza na pagina web (redirect_to).
ipcMain.handle("auth-recover", async (_e, { email } = {}) => {
  const s = loadConfig().sessionEnc;
  const mail = (email || (s && s.email) || "").trim();
  if (!mail) return { ok: false, error: "Informe um email." };
  const redirect = encodeURIComponent(`${API_BASE}/redefinir-senha`);
  try {
    const { status, data } = await supabaseAuth(`recover?redirect_to=${redirect}`, { email: mail });
    if (status === 200) return { ok: true };
    return { ok: false, error: authError(data, "Não foi possível enviar o email.") };
  } catch {
    return { ok: false, error: "Sem internet ou Supabase fora do ar." };
  }
});

// Apaga os dados locais (chave, sessao, prefs, onboarding) — NAO mexe nos clips.
ipcMain.handle("wipe-local-data", () => {
  saveConfig({});
  return { ok: true };
});

// Exclui a conta no servidor (service_role, server-side) e limpa os dados locais.
ipcMain.handle("auth-delete-account", async () => {
  const token = await getValidAccessToken();
  if (!token) return { ok: false, error: "Sessão expirada. Entre novamente." };
  try {
    const r = await fetch(`${API_BASE}/api/account/delete`, {
      method: "POST",
      headers: { Authorization: "Bearer " + token },
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok && data.ok) {
      saveConfig({}); // conta excluida -> zera o estado local
      return { ok: true };
    }
    return { ok: false, error: data.error || "Servidor respondeu " + r.status + "." };
  } catch {
    return { ok: false, error: "Sem internet ou servidor fora do ar." };
  }
});

// Retorna a sessao salva; renova com o refresh_token se o access_token expirou.
ipcMain.handle("auth-get-session", async () => {
  const s = loadConfig().sessionEnc;
  if (!s || !s.refresh) return null;
  if (s.expires_at && s.expires_at * 1000 > Date.now() + 60_000) {
    syncAcceptance(); // backfill/retry da prova de aceite (background)
    return { email: s.email };
  }
  const refreshToken = decryptSecret(s.refresh);
  if (!refreshToken) return null;
  try {
    const { status, data } = await supabaseAuth("token?grant_type=refresh_token", {
      refresh_token: refreshToken,
    });
    if (status === 200 && data.access_token) {
      storeSession(data);
      syncAcceptance(); // backfill/retry da prova de aceite (background)
      return { email: data.user && data.user.email };
    }
  } catch {
    return { email: s.email }; // offline: mantem a sessao local ate reconectar
  }
  storeSession(null);
  return null;
});

ipcMain.handle("get-key", () => decryptSecret(loadConfig().keyEnc));
ipcMain.handle("set-key", (_e, k) => {
  const c = loadConfig();
  c.keyEnc = k ? encryptSecret(k) : null;
  saveConfig(c);
  return true;
});

// --- Pasta dos clips (escolhida no onboarding) ---
ipcMain.handle("get-library-dir", () => ({
  dir: loadConfig().libraryDir || null,
  defaultDir: defaultLibraryDir(),
}));
ipcMain.handle("pick-library-dir", async () => {
  const c = loadConfig();
  const r = await dialog.showOpenDialog(win, {
    title: "Escolha a pasta dos clips",
    defaultPath: c.libraryDir || defaultLibraryDir(),
    properties: ["openDirectory", "createDirectory"],
  });
  return r.canceled ? null : r.filePaths[0];
});
ipcMain.handle("set-library-dir", (_e, dir) => {
  if (!dir || typeof dir !== "string") return { ok: false };
  const c = loadConfig();
  c.libraryDir = dir;
  saveConfig(c);
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    /* a pasta pode ja existir ou ser criada na 1a geracao */
  }
  return { ok: true, dir };
});

// Prova de aceite: grava no Supabase (trilha de auditoria) usando a sessao do user.
async function recordAcceptance(version, accepts, acceptedAt) {
  const token = await getValidAccessToken();
  if (!token) return false;
  try {
    const r = await fetch(`${SUPABASE_URL}/rest/v1/legal_acceptances`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: SUPABASE_ANON_KEY,
        Authorization: "Bearer " + token,
        Prefer: "return=minimal",
      },
      body: JSON.stringify({
        version,
        accepts: accepts || {},
        app_version: app.getVersion(),
        accepted_at: acceptedAt || new Date().toISOString(),
      }),
    });
    return r.ok; // 201 Created
  } catch {
    return false;
  }
}

// Garante que o aceite local esteja registrado no banco (best-effort + retry).
// Cobre: novo aceite, re-aceite, retry offline e backfill de aceites locais antigos.
async function syncAcceptance() {
  const c = loadConfig();
  const ob = c.onboarding;
  if (!ob || ob.synced) return;
  const ok = await recordAcceptance(ob.version, ob.accepts, ob.acceptedAt);
  if (ok) {
    const c2 = loadConfig();
    if (c2.onboarding && c2.onboarding.version === ob.version) {
      c2.onboarding.synced = true;
      saveConfig(c2);
    }
  }
}

// --- Onboarding de primeiro acesso (aceites + pasta) ---
const LEGAL_VERSION = "2026-06-19";
ipcMain.handle("get-onboarding", () => {
  const c = loadConfig();
  const ob = c.onboarding;
  const accepted = Boolean(ob && ob.version === LEGAL_VERSION);
  return {
    done: accepted && Boolean(c.libraryDir),
    libraryDir: c.libraryDir || null,
    defaultDir: defaultLibraryDir(),
    legalVersion: LEGAL_VERSION,
  };
});
ipcMain.handle("complete-onboarding", (_e, payload = {}) => {
  const a = payload.accepts || {};
  const allAccepted = ["terms", "privacy", "content", "age"].every((k) => a[k] === true);
  const dir = payload.libraryDir;
  if (!allAccepted) return { ok: false, error: "Aceite todos os itens para continuar." };
  if (!dir || typeof dir !== "string") return { ok: false, error: "Escolha uma pasta para os clips." };

  const c = loadConfig();
  c.libraryDir = dir;
  c.onboarding = {
    version: LEGAL_VERSION,
    acceptedAt: new Date().toISOString(),
    accepts: a,
    synced: false,
  };
  saveConfig(c);
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    /* idem */
  }
  syncAcceptance(); // grava a prova no banco em background (retry no proximo boot)
  return { ok: true };
});

ipcMain.handle("open-folder", (_e, p) => shell.openPath(p || libraryRoot()));

// Busca somente metadados publicos do YouTube para confirmar o link na interface.
ipcMain.handle("get-link-preview", async (_e, rawUrl) => {
  if (!isYoutubeUrl(rawUrl)) {
    return { ok: false, unsupported: true };
  }

  const videoId = youtubeVideoId(rawUrl);
  if (!videoId) {
    return { ok: false, error: "COLE UM LINK VÁLIDO DO YOUTUBE" };
  }

  const canonicalUrl = `https://www.youtube.com/watch?v=${videoId}`;
  const endpoint = `https://www.youtube.com/oembed?url=${encodeURIComponent(canonicalUrl)}&format=json`;

  try {
    const response = await fetchWithTimeout(endpoint, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return { ok: false, error: "VÍDEO INDISPONÍVEL OU PRIVADO" };
    }

    const data = await response.json();
    let thumbnail = null;
    try {
      thumbnail = await thumbnailDataUrl(data.thumbnail_url);
    } catch {
      // A confirmação textual continua útil quando a miniatura não responde.
    }

    return {
      ok: true,
      provider: "YOUTUBE",
      title: String(data.title || "Vídeo do YouTube"),
      authorName: String(data.author_name || "Canal não informado"),
      canonicalUrl,
      thumbnail,
    };
  } catch {
    return { ok: false, error: "NÃO FOI POSSÍVEL CARREGAR A PRÉVIA" };
  }
});

// Valida a chave na OpenRouter (e traz info de credito). NAO gera custo.
ipcMain.handle("validate-key", async (_e, key) => {
  key = (key || "").trim();
  if (key.length < 8) return { valid: false, error: "Cole a sua chave." };
  try {
    const r = await fetch("https://openrouter.ai/api/v1/auth/key", {
      headers: { Authorization: "Bearer " + key },
    });
    if (r.status === 200) {
      const d = ((await r.json()) || {}).data || {};
      return {
        valid: true,
        label: d.label || null,
        usage: d.usage ?? null,
        limit: d.limit ?? null,
        limitRemaining: d.limit_remaining ?? null,
        freeTier: d.is_free_tier ?? null,
      };
    }
    if (r.status === 401) return { valid: false, error: "Chave inválida ou expirada." };
    return { valid: false, error: "OpenRouter respondeu " + r.status + "." };
  } catch (e) {
    return { valid: false, error: "Sem internet / OpenRouter fora do ar." };
  }
});

ipcMain.handle("get-stats", () => {
  const c = loadConfig();
  return { totalCost: c.totalCost || 0, totalTokens: c.totalTokens || 0 };
});

// Lista os cortes ja gerados (varre as subpastas por run + le os manifests).
ipcMain.handle("list-clips", () => {
  const root = libraryRoot();
  const out = [];
  let runs;
  try {
    runs = fs.readdirSync(root, { withFileTypes: true }).filter((d) => d.isDirectory());
  } catch {
    return [];
  }
  // mais novo primeiro (subpasta = timestamp)
  runs.sort((a, b) => b.name.localeCompare(a.name));
  for (const r of runs) {
    const dir = path.join(root, r.name);
    let manifest = {};
    try {
      manifest = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
    } catch {
      /* sem manifest */
    }
    const byFile = {};
    (manifest.clips || []).forEach((c) => (byFile[c.file] = c));
    let files;
    try {
      files = fs.readdirSync(dir).filter((f) => f.endsWith(".mp4") && !f.endsWith(".cap.mp4"));
    } catch {
      files = [];
    }
    files.sort();
    for (const f of files) {
      const meta = byFile[f] || {};
      out.push({
        file: f,
        url: "zclip://" + encodeURIComponent(path.join(dir, f)),
        path: path.join(dir, f),
        run: r.name,
        hook: meta.hook || "",
        description: meta.description || "",
        virality_score: meta.virality_score ?? null,
        duration_s: meta.start != null && meta.end != null ? meta.end - meta.start : null,
      });
    }
  }
  return out;
});

ipcMain.on("generate", (_e, opts) => {
  if (child) return;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const out = path.join(libraryRoot(), stamp);
  fs.mkdirSync(out, { recursive: true });

  const args = [
    opts.source,
    "--out", out,
    "--clips", String(opts.clips),
    "--min-len", String(opts.minLen),
    "--max-len", String(opts.maxLen),
    "--layout", opts.layout,
    "--facecam", opts.facecam,
  ];
  if (!opts.captions) args.push("--no-captions");
  if (opts.key) args.push("--key", opts.key);

  try {
    child = spawn(enginePath(), args, { env: engineEnv() });
  } catch (e) {
    win.webContents.send("job-error", { message: "Não consegui iniciar o motor: " + e.message });
    return;
  }

  const rl = readline.createInterface({ input: child.stdout });
  rl.on("line", (line) => {
    line = line.trim();
    if (!line) return;
    try {
      const msg = JSON.parse(line);
      if (msg.type === "progress") win.webContents.send("job-progress", msg);
      else if (msg.type === "done") {
        const c = loadConfig();
        const cost = msg.cost || {};
        c.totalCost = (c.totalCost || 0) + (cost.cost_usd || 0);
        c.totalTokens = (c.totalTokens || 0) + (cost.total_tokens || 0);
        saveConfig(c);
        win.webContents.send("job-done", {
          ...msg, out,
          totals: { totalCost: c.totalCost, totalTokens: c.totalTokens },
        });
      } else if (msg.type === "warning") win.webContents.send("job-warning", msg);
      else if (msg.type === "error") win.webContents.send("job-error", msg);
    } catch {
      /* log do ffmpeg/whisper — ignora */
    }
  });

  let err = "";
  child.stderr.on("data", (d) => (err += d.toString()));
  child.on("close", (code) => {
    child = null;
    if (code !== 0) {
      win.webContents.send("job-error", {
        message: "O motor encerrou com erro (código " + code + ").",
        detail: err.slice(-400),
      });
    }
  });
  child.on("error", (e2) => {
    child = null;
    win.webContents.send("job-error", { message: "Não consegui iniciar o motor: " + e2.message });
  });
});
