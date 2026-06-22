// Processo principal do Electron: janela, chave, dispara o BINARIO do motor
// (medusacut-engine), repassa o progresso (JSON), e serve a biblioteca local.

const { app, BrowserWindow, ipcMain, dialog, shell, protocol, net, safeStorage, clipboard } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const readline = require("readline");
const crypto = require("crypto");
const { pathToFileURL } = require("url");

// Clipes servidos por ID (zclip://clip/<id>), nao por caminho na URL: scheme
// "standard" faz lowercase do host e quebrava caminhos absolutos (ex.: /Users).
// O registry tambem e um allowlist (so toca o que listClips registrou).
const clipRegistry = new Map();
function registerClip(absPath) {
  const id = crypto.createHash("sha1").update(absPath).digest("hex").slice(0, 16);
  clipRegistry.set(id, absPath);
  return id;
}

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

// Provedores de IA suportados (BYO key). A chave de cada um fica cifrada no disco,
// separada por provedor, pra o usuario alternar sem reconectar.
const PROVIDERS = ["openrouter", "openai", "anthropic"];
function normProvider(p) {
  return PROVIDERS.includes(p) ? p : "openrouter";
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
  // Chave unica antiga (so OpenRouter) -> mapa por provedor.
  if (c.keyEnc && !c.keysEnc) {
    c.keysEnc = { openrouter: c.keyEnc };
    delete c.keyEnc;
    changed = true;
  }
  if (!c.provider) {
    c.provider = "openrouter";
    changed = true;
  }
  // sessao/conta antigas (app tinha login): limpa qualquer residuo no config.
  if (c.session || c.sessionEnc) {
    delete c.session;
    delete c.sessionEnc;
    changed = true;
  }

  c.secretsPlaintext = !secretsEncrypted();
  if (changed) saveConfig(c);
}

// App sem cadastro: nao ha login/conta nem backend. Aceite legal e gravado so local
// (config.json em userData); nada de video/clipe/conta sobe pra nuvem.

function enginePath() {
  if (process.env.ENGINE_BIN) return process.env.ENGINE_BIN;
  // No Windows o binario do PyInstaller é medusacut-engine.exe.
  const bin = process.platform === "win32" ? "medusacut-engine.exe" : "medusacut-engine";
  const base = app.isPackaged ? process.resourcesPath : __dirname; // dev: engine/ montada
  return path.join(base, "engine", bin);
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

// Icone do app (mesmo do instalador). Em dev (npm start) o Electron usaria o icone
// padrao dele; aqui forcamos o da Medusa na janela/taskbar (Win/Linux) e no dock (Mac).
const APP_ICON = path.join(__dirname, "build", "icon.png");

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 700,
    backgroundColor: "#060608",
    title: "Medusa Clip",
    icon: APP_ICON,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Endurecimento: nada navega DENTRO da janela Electron. Links externos abrem no
  // navegador do sistema; window.open/target=_blank são negados.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (url !== win.webContents.getURL()) {
      e.preventDefault();
      if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    }
  });
}

// --- Auto-update (electron-updater). Fluxo "avisar antes de baixar":
//   update-available  -> renderer mostra "nova versao vX  [BAIXAR]"
//   usuario aceita     -> update-download -> progresso -> update-ready
//   renderer mostra "[REINICIAR PRA INSTALAR]" -> update-install -> quitAndInstall()
// macOS NAO assinado nao consegue trocar o proprio binario (Squirrel.Mac exige
// assinatura/notarizacao): nesse caso so checamos a ultima release e mandamos o
// usuario baixar no site (evento update-site). Trocar pelo fluxo nativo ao assinar.
const GITHUB_REPO = "Edualnog/medusa-clip"; // mesmo repo publico (open source, AGPL-3.0); releases vivem aqui
const DOWNLOAD_PAGE = process.env.MEDUSA_DOWNLOAD_PAGE || "https://medusaclip.com/#download";

function sendToWin(channel, payload) {
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload);
}

// Compara versoes "a.b.c" numericamente; true se `a` for maior que `b`.
function isNewerVersion(a, b) {
  const pa = String(a).split(".").map(Number);
  const pb = String(b).split(".").map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d !== 0) return d > 0;
  }
  return false;
}

// Update do Mac (app NAO assinado): o swap nativo do Squirrel.Mac exige assinatura,
// entao em vez de auto-instalar a gente BAIXA o .dmg da release e ABRE o instalador
// (o usuario arrasta pra Applications). Guardamos o asset achado aqui pra o download
// nao depender de URL vinda do renderer (defesa contra renderer comprometido).
let pendingMacUpdate = null; // { version, dmgUrl, dmgName }

async function checkMacUpdate() {
  if (GITHUB_REPO.includes("PLACEHOLDER")) return;
  try {
    const r = await fetchWithTimeout(
      `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`,
      { headers: { Accept: "application/vnd.github+json" } }
    );
    if (!r.ok) return;
    const data = await r.json();
    const latest = String(data.tag_name || "").replace(/^v/, "");
    if (!latest || !isNewerVersion(latest, app.getVersion())) return;

    // Acha o instalador do Mac (.dmg) na release. So buildamos arm64 (Apple Silicon).
    const asset = (data.assets || []).find(
      (a) => /mac/i.test(a.name || "") && String(a.name).endsWith(".dmg")
    );
    if (asset && asset.browser_download_url) {
      pendingMacUpdate = { version: latest, dmgUrl: asset.browser_download_url, dmgName: asset.name };
    }
    sendToWin("update-site", { version: latest, url: DOWNLOAD_PAGE, canAutoDownload: Boolean(pendingMacUpdate) });
  } catch {
    /* update nunca derruba o app */
  }
}

// Baixa um arquivo via fetch (segue redirect), reportando progresso (%), com backpressure.
async function downloadFile(url, destPath, onProgress) {
  const { Readable, Transform } = require("stream");
  const { pipeline } = require("stream/promises");
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok || !res.body) throw new Error("download respondeu " + res.status);
  const total = Number(res.headers.get("content-length") || 0);
  let received = 0;
  const counter = new Transform({
    transform(chunk, _enc, cb) {
      received += chunk.length;
      if (total && onProgress) onProgress(Math.round((received / total) * 100));
      cb(null, chunk);
    },
  });
  await pipeline(Readable.fromWeb(res.body), counter, fs.createWriteStream(destPath));
}

// Mac: baixa o .dmg da release pra ~/Downloads e abre o instalador. So aceita URLs
// do GitHub (a info vem do nosso checkMacUpdate, nao do renderer).
ipcMain.handle("download-mac-update", async () => {
  const info = pendingMacUpdate;
  if (!info || !info.dmgUrl) {
    shell.openExternal(DOWNLOAD_PAGE);
    return { ok: false, error: "Sem instalador para baixar." };
  }
  let host = "";
  try {
    host = new URL(info.dmgUrl).hostname.toLowerCase();
  } catch {
    host = "";
  }
  const allowed = host === "github.com" || host.endsWith(".github.com") || host.endsWith(".githubusercontent.com");
  if (!allowed) {
    shell.openExternal(DOWNLOAD_PAGE);
    return { ok: false, error: "Origem do download não confiável." };
  }
  const dest = path.join(app.getPath("downloads"), info.dmgName || "MedusaClip-mac-arm64.dmg");
  try {
    sendToWin("update-progress", { percent: 0 });
    await downloadFile(info.dmgUrl, dest, (pct) => sendToWin("update-progress", { percent: pct }));
    await shell.openPath(dest); // abre o .dmg (Finder mostra arrastar -> Applications)
    sendToWin("mac-update-opened", { version: info.version, path: dest });
    return { ok: true, path: dest };
  } catch (e) {
    sendToWin("mac-update-error", { message: (e && e.message) || "Falha no download." });
    return { ok: false, error: (e && e.message) || "Falha no download." };
  }
});

function setupUpdates() {
  if (!app.isPackaged) return; // dev (npm start): nao checa update
  if (process.platform === "darwin") {
    checkMacUpdate();
    return;
  }
  if (GITHUB_REPO.includes("PLACEHOLDER")) return; // repo ainda nao configurado

  let autoUpdater;
  try {
    ({ autoUpdater } = require("electron-updater"));
  } catch {
    return; // dep ausente -> segue sem update
  }
  autoUpdater.autoDownload = false; // "avisar antes de baixar"
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("update-available", (info) => sendToWin("update-available", { version: info.version }));
  autoUpdater.on("download-progress", (p) => sendToWin("update-progress", { percent: Math.round(p.percent || 0) }));
  autoUpdater.on("update-downloaded", (info) => sendToWin("update-ready", { version: info.version }));
  autoUpdater.on("error", (err) => console.error("[update]", err && err.message));

  ipcMain.handle("update-download", () =>
    autoUpdater.downloadUpdate().catch((e) => console.error("[update]", e && e.message))
  );
  ipcMain.handle("update-install", () => autoUpdater.quitAndInstall());

  autoUpdater.checkForUpdates().catch((e) => console.error("[update]", e && e.message));
}

app.setName("Medusa Clip"); // sem isso o menu/dock em dev aparece como "Electron"

app.whenReady().then(() => {
  migrateConfig(); // safeStorage so fica disponivel apos o ready
  // Dock do macOS em dev: o icone do bundle so existe no build empacotado; aqui
  // forcamos o icone da Medusa pra nao aparecer o do Electron ao rodar npm start.
  if (process.platform === "darwin" && app.dock) {
    try {
      app.dock.setIcon(APP_ICON);
    } catch {
      /* icone ausente: mantem o padrao */
    }
  }
  // zclip://clip/<id> -> serve o video local correspondente (id registrado em listClips).
  protocol.handle("zclip", (request) => {
    let id = "";
    try {
      id = new URL(request.url).pathname.replace(/^\/+/, "");
    } catch {
      id = "";
    }
    const p = clipRegistry.get(id);
    // So serve ids registrados E dentro da pasta de clips (defesa em profundidade).
    const root = path.normalize(libraryRoot());
    if (!p || (p !== root && !p.startsWith(root + path.sep))) {
      return new Response("forbidden", { status: 403 });
    }
    return net.fetch(pathToFileURL(p).toString());
  });
  createWindow();
  setupUpdates(); // checa atualizacao ao abrir (so em build empacotado)
});
app.on("window-all-closed", () => app.quit());
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.handle("get-version", () => app.getVersion());
ipcMain.handle("open-download-page", () => shell.openExternal(DOWNLOAD_PAGE));
ipcMain.handle("open-github", () => shell.openExternal(`https://github.com/${GITHUB_REPO}/releases`));
// Abre links de suporte/comunidade no navegador (https) ou cliente de e-mail (mailto).
// Restrito a https/mailto pra nao abrir esquemas arbitrarios vindos do renderer.
ipcMain.handle("open-external", (_e, url) => {
  if (typeof url !== "string") return;
  if (/^https:\/\//i.test(url) || /^mailto:/i.test(url)) shell.openExternal(url);
});
// Copia texto pro clipboard (usado pelo "convidar amigos").
ipcMain.handle("copy-text", (_e, text) => {
  if (typeof text === "string") clipboard.writeText(text);
});
ipcMain.handle("pick-file", async () => {
  const r = await dialog.showOpenDialog(win, {
    properties: ["openFile"],
    filters: [{ name: "Vídeo", extensions: ["mp4", "mov", "mkv", "webm"] }],
  });
  return r.canceled ? null : r.filePaths[0];
});
// Apaga os dados locais (chave, prefs, onboarding) — NAO mexe nos clips.
ipcMain.handle("wipe-local-data", () => {
  saveConfig({});
  return { ok: true };
});

// --- Provedor de IA ativo (OpenRouter / OpenAI / Anthropic) ---
ipcMain.handle("get-provider", () => normProvider(loadConfig().provider));

// Quais provedores já têm chave salva (só presença, SEM descriptografar — assim não
// disparamos o cofre do SO/Keychain só pra montar os badges do seletor).
ipcMain.handle("get-connected-providers", () => {
  const keys = loadConfig().keysEnc || {};
  return PROVIDERS.filter((p) => {
    const box = keys[p];
    return Boolean(box && box.d);
  });
});
ipcMain.handle("set-provider", (_e, p) => {
  const c = loadConfig();
  c.provider = normProvider(p);
  saveConfig(c);
  return c.provider;
});

// Devolve { key, status }: "empty" (nenhuma salva), "locked" (há chave salva mas o
// cofre do SO não liberou — ex.: usuário clicou "Negar" no Keychain) ou "ok".
// O "locked" deixa a UI avisar "reconecte a chave" em vez de só vir vazio sem explicar.
// `provider` opcional: padrao = provedor ativo no config.
ipcMain.handle("get-key", (_e, provider) => {
  const c = loadConfig();
  const prov = normProvider(provider || c.provider);
  const box = (c.keysEnc || {})[prov];
  if (!box) return { key: "", status: "empty" };
  if (box.v === "enc") {
    try {
      const key = safeStorage.decryptString(Buffer.from(box.d, "base64"));
      return key ? { key, status: "ok" } : { key: "", status: "locked" };
    } catch {
      return { key: "", status: "locked" };
    }
  }
  return box.d ? { key: box.d, status: "ok" } : { key: "", status: "empty" };
});
ipcMain.handle("set-key", (_e, provider, k) => {
  const c = loadConfig();
  const prov = normProvider(provider || c.provider);
  c.keysEnc = c.keysEnc || {};
  c.keysEnc[prov] = k ? encryptSecret(k) : null;
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

// --- Onboarding de primeiro acesso (aceites + pasta) ---
const LEGAL_VERSION = "2026-06-21";
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
  // Prova de aceite gravada SO localmente (sem servidor): versao + data + itens.
  c.onboarding = {
    version: LEGAL_VERSION,
    acceptedAt: new Date().toISOString(),
    accepts: a,
    appVersion: app.getVersion(),
  };
  saveConfig(c);
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    /* idem */
  }
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

// Valida a chave no provedor escolhido. NAO gera custo (endpoints de metadados).
ipcMain.handle("validate-key", async (_e, provider, key) => {
  const prov = normProvider(provider);
  key = (key || "").trim();
  if (key.length < 8) return { valid: false, error: "Cole a sua chave." };
  if (prov === "openrouter") return validateOpenRouter(key);
  if (prov === "openai") return validateOpenAI(key);
  return validateAnthropic(key);
});

async function validateOpenRouter(key) {
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
  } catch {
    return { valid: false, error: "Sem internet / OpenRouter fora do ar." };
  }
}

// OpenAI: lista de modelos autentica a chave sem consumir tokens.
async function validateOpenAI(key) {
  try {
    const r = await fetch("https://api.openai.com/v1/models", {
      headers: { Authorization: "Bearer " + key },
    });
    if (r.status === 200) return { valid: true };
    if (r.status === 401) return { valid: false, error: "Chave inválida ou expirada." };
    if (r.status === 429) return { valid: false, error: "Sem crédito ou limite atingido na OpenAI." };
    return { valid: false, error: "OpenAI respondeu " + r.status + "." };
  } catch {
    return { valid: false, error: "Sem internet / OpenAI fora do ar." };
  }
}

// Anthropic: GET /v1/models autentica sem consumir tokens (x-api-key + version).
async function validateAnthropic(key) {
  try {
    const r = await fetch("https://api.anthropic.com/v1/models", {
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01" },
    });
    if (r.status === 200) return { valid: true };
    if (r.status === 401) return { valid: false, error: "Chave inválida ou expirada." };
    return { valid: false, error: "Anthropic respondeu " + r.status + "." };
  } catch {
    return { valid: false, error: "Sem internet / Anthropic fora do ar." };
  }
}

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
      const full = path.join(dir, f);
      let mtime = 0;
      try {
        mtime = fs.statSync(full).mtimeMs;
      } catch {
        /* arquivo sumiu entre o readdir e o stat */
      }
      // Thumbnail (capa) do corte, se gerada: serve pelo mesmo protocolo (allowlist).
      let thumbUrl = null;
      let thumbPath = null;
      const thumbName = meta.thumb || `${f.replace(/\.mp4$/, "")}.jpg`;
      if (thumbName) {
        const tp = path.join(dir, thumbName);
        if (fs.existsSync(tp)) {
          thumbPath = tp;
          thumbUrl = "zclip://clip/" + registerClip(tp);
        }
      }
      out.push({
        file: f,
        url: "zclip://clip/" + registerClip(full),
        path: full,
        thumbUrl,
        thumbPath,
        run: r.name,
        mtime,
        hook: meta.hook || "",
        description: meta.description || "",
        virality_score: meta.virality_score ?? null,
        start: meta.start ?? null,
        end: meta.end ?? null,
        duration_s: meta.start != null && meta.end != null ? meta.end - meta.start : null,
      });
    }
  }
  return out;
});

ipcMain.on("generate", (_e, opts) => {
  if (child) return;

  // Valida a fonte ANTES de chamar o motor: aceita só arquivo local existente OU link
  // do YouTube. Bloqueia file://, URLs internas/aleatórias e outros esquemas que o
  // yt-dlp tentaria abrir (evita SSRF / leitura de caminho inesperado).
  const src = String((opts && opts.source) || "").trim();
  let validSource = false;
  try {
    validSource = fs.existsSync(src) || isYoutubeUrl(src);
  } catch {
    validSource = false;
  }
  if (!validSource) {
    win.webContents.send("job-error", {
      message: "Fonte inválida: escolha um arquivo de vídeo local ou cole um link público do YouTube.",
    });
    return;
  }

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
  if (opts.thumbnails === false) args.push("--no-thumbs");
  if (opts.thumbAi === true) args.push("--thumb-ai");

  // A chave vai por VARIÁVEL DE AMBIENTE (LLM_API_KEY), nunca por argv: argumentos
  // de processo são visíveis a outros processos/usuários locais (ps -ef). O motor lê
  // LLM_PROVIDER + LLM_API_KEY do ambiente; o --key fica só pra uso manual do binário.
  const env = engineEnv();
  env.LLM_PROVIDER = normProvider(opts.provider);
  if (opts.key) env.LLM_API_KEY = opts.key;

  try {
    child = spawn(enginePath(), args, { env });
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
