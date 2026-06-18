// Processo principal do Electron: janela, chave, dispara o BINARIO do motor
// (medusacut-engine), repassa o progresso (JSON), e serve a biblioteca local.

const { app, BrowserWindow, ipcMain, dialog, shell, protocol, net } = require("electron");
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

function libraryRoot() {
  const dir = path.join(app.getPath("downloads"), "Medusa Clip");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
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
ipcMain.handle("get-key", () => loadConfig().key || "");
ipcMain.handle("set-key", (_e, k) => {
  const c = loadConfig();
  c.key = k;
  saveConfig(c);
  return true;
});
ipcMain.handle("open-folder", (_e, p) => shell.openPath(p || libraryRoot()));

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
