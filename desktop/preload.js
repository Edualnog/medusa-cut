// Ponte segura entre a UI (renderer) e o processo principal.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  pickFile: () => ipcRenderer.invoke("pick-file"),
  getKey: () => ipcRenderer.invoke("get-key"),
  setKey: (k) => ipcRenderer.invoke("set-key", k),
  openFolder: (p) => ipcRenderer.invoke("open-folder", p),
  generate: (opts) => ipcRenderer.send("generate", opts),
  onProgress: (cb) => ipcRenderer.on("job-progress", (_e, m) => cb(m)),
  onDone: (cb) => ipcRenderer.on("job-done", (_e, m) => cb(m)),
  onError: (cb) => ipcRenderer.on("job-error", (_e, m) => cb(m)),
});
