// Processo principal do Electron: cria a janela, guarda a chave, dispara o BINARIO
// do motor (medusacut-engine) e repassa o progresso (JSON por linha) pra UI.

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const readline = require("readline");

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

// Caminho do binario do motor: env em dev, recurso embutido no app empacotado.
function enginePath() {
  if (process.env.ENGINE_BIN) return process.env.ENGINE_BIN;
  if (app.isPackaged) return path.join(process.resourcesPath, "engine", "medusacut-engine");
  return "/tmp/medusa_e2e/dist/medusacut-engine/medusacut-engine";
}

function outputDir() {
  const dir = path.join(app.getPath("downloads"), "Zorothax");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function createWindow() {
  win = new BrowserWindow({
    width: 1000,
    height: 800,
    backgroundColor: "#0a0a0d",
    title: "Zorothax",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile(path.join(__dirname, "renderer", "index.html"));
}

app.whenReady().then(createWindow);
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
ipcMain.handle("open-folder", (_e, p) => shell.openPath(p || outputDir()));

ipcMain.on("generate", (_e, opts) => {
  if (child) return; // um job por vez
  const out = outputDir();
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
    child = spawn(enginePath(), args, { env: process.env });
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
      else if (msg.type === "done") win.webContents.send("job-done", { ...msg, out });
      else if (msg.type === "error") win.webContents.send("job-error", msg);
    } catch {
      /* linha nao-JSON (log do ffmpeg/whisper) — ignora */
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
