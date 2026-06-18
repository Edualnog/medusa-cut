// Interface do app desktop. Toda integracao nativa passa pela ponte segura do preload.
const $ = (id) => document.getElementById(id);

const VIEW_META = {
  inicio: { title: "INÍCIO", code: "01" },
  biblioteca: { title: "BIBLIOTECA", code: "02" },
  apis: { title: "CHAVES API", code: "03" },
};

const LAYOUT_LABELS = {
  facecam_top_gameplay_bottom: "FACECAM + GAMEPLAY",
  dynamic_gameplay: "SEGUE A AÇÃO",
  gameplay_blur: "FUNDO DESFOCADO",
};

const DURATION_LABELS = {
  "15,90": "AUTO · 15–90S",
  "10,40": "CURTOS · 10–40S",
  "60,180": "LONGOS · 60–180S",
};

let mode = "file";
let filePath = null;
let isProcessing = false;
let lastWarning = "";
let libraryClips = [];

function setView(view) {
  document.querySelectorAll(".nav").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  Object.keys(VIEW_META).forEach((id) => {
    $("view-" + id).classList.toggle("hidden", id !== view);
  });

  $("topSectionTitle").textContent = VIEW_META[view].title;
  $("topSectionCode").textContent = VIEW_META[view].code;

  if (view === "biblioteca") loadLibrary();
  if (view === "apis") {
    loadStats();
    if ($("key").value.trim()) checkKey();
  }
}

document.querySelectorAll(".nav").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

function setMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  $("srcFile").classList.toggle("hidden", mode !== "file");
  $("srcLink").classList.toggle("hidden", mode !== "link");
  updateSummary();
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

$("srcFile").addEventListener("click", async () => {
  const path = await window.api.pickFile();
  if (!path) return;
  filePath = path;
  $("fileName").textContent = path.split(/[\\/]/).pop();
  $("fileName").classList.remove("placeholder");
  updateSummary();
});

$("linkInput").addEventListener("input", updateSummary);
$("layout").addEventListener("change", updateSummary);
$("dur").addEventListener("change", updateSummary);
$("facecam").addEventListener("change", updateSummary);
$("captions").addEventListener("change", updateSummary);
$("clips").addEventListener("input", updateSummary);

function sourceReady() {
  return mode === "file" ? Boolean(filePath) : $("linkInput").value.trim().length > 6;
}

function updateSummary() {
  const clips = Number($("clips").value);
  const selectedLayout = $("layout").value;
  const facecamLayout = selectedLayout === "facecam_top_gameplay_bottom";

  $("clipsN").textContent = `${clips} ${clips === 1 ? "CLIP" : "CLIPS"}`;
  $("summarySource").textContent = sourceReady()
    ? (mode === "file" ? $("fileName").textContent : "LINK PÚBLICO")
    : "NÃO SELECIONADA";
  $("summaryLayout").textContent = LAYOUT_LABELS[selectedLayout] || "PERSONALIZADO";
  $("summaryDuration").textContent = DURATION_LABELS[$("dur").value] || "PERSONALIZADA";
  $("summaryClips").textContent = `${clips} ${clips === 1 ? "CLIP" : "CLIPS"}`;
  $("summaryCaptions").textContent = $("captions").checked ? "ATIVADAS" : "DESATIVADAS";
  $("facecamField").classList.toggle("hidden", !facecamLayout);
  $("facecam").disabled = !facecamLayout;
  $("gen").disabled = !sourceReady() || isProcessing;
}

window.api.getKey().then((key) => {
  if (!key) return;
  $("key").value = key;
  $("keyHelper").textContent = "Chave OpenRouter salva neste computador.";
  $("keyHelper").classList.add("ready");
});

$("toggleKey").addEventListener("click", () => {
  const showing = $("key").type === "text";
  $("key").type = showing ? "password" : "text";
  $("toggleKey").textContent = showing ? "MOSTRAR" : "OCULTAR";
});

function setKeyStatus(text, state = "") {
  $("keyStatus").textContent = text;
  $("keyStatus").className = `key-status${state ? " " + state : ""}`;
}

async function checkKey() {
  const key = $("key").value.trim();
  if (!key) {
    setKeyStatus("COLE SUA CHAVE PARA CONTINUAR", "invalid");
    return false;
  }

  setKeyStatus("VERIFICANDO NA OPENROUTER…", "loading");
  const result = await window.api.validateKey(key);
  if (!result.valid) {
    setKeyStatus(result.error || "CHAVE INVÁLIDA", "invalid");
    return false;
  }

  let extra = "";
  if (result.limitRemaining != null) extra = ` · RESTA $${Number(result.limitRemaining).toFixed(2)}`;
  else if (result.usage != null) extra = ` · USADO $${Number(result.usage).toFixed(4)}`;
  setKeyStatus(`CHAVE VÁLIDA${result.freeTier ? " · FREE TIER" : ""}${extra}`, "valid");
  $("keyHelper").textContent = "Chave OpenRouter verificada e pronta.";
  $("keyHelper").classList.add("ready");
  return true;
}

$("saveKey").addEventListener("click", async () => {
  const key = $("key").value.trim();
  $("saveKey").disabled = true;
  $("saveKey").textContent = "VERIFICANDO…";
  const valid = await checkKey();
  if (valid) await window.api.setKey(key);
  $("saveKey").disabled = false;
  $("saveKey").textContent = "SALVAR E VERIFICAR";
});

async function loadStats() {
  const stats = await window.api.getStats();
  $("costTotal").textContent = "$" + Number(stats.totalCost || 0).toFixed(4);
  $("costTokens").textContent = Number(stats.totalTokens || 0).toLocaleString("pt-BR");
}

$("gen").addEventListener("click", async () => {
  const key = $("key").value.trim();
  if (!key) {
    setView("apis");
    setKeyStatus("CONECTE SUA CHAVE ANTES DE GERAR", "invalid");
    $("key").focus();
    return;
  }

  const [minLen, maxLen] = $("dur").value.split(",").map(Number);
  const source = mode === "file" ? filePath : $("linkInput").value.trim();
  await window.api.setKey(key);
  startUI();
  window.api.generate({
    source,
    key,
    clips: Number($("clips").value),
    minLen,
    maxLen,
    layout: $("layout").value,
    facecam: $("facecam").value,
    captions: $("captions").checked,
  });
});

function startUI() {
  lastWarning = "";
  isProcessing = true;
  $("appStatus").textContent = "PROCESSANDO";
  $("prog").classList.add("show");
  $("prog").classList.remove("error");
  $("pstate").textContent = "PROCESSANDO";
  $("result").replaceChildren();
  setProg(2, "Iniciando o motor local…");
  updateSummary();
}

function finishProcessing(status = "PRONTO") {
  isProcessing = false;
  $("appStatus").textContent = status;
  updateSummary();
}

function setProg(percent, stage) {
  $("pfill").style.width = Math.min(100, Math.max(0, percent)) + "%";
  $("ppct").textContent = Math.round(percent) + "%";
  if (stage) $("pstage").textContent = stage;
}

function resultMessage(text, type = "") {
  const message = document.createElement("div");
  message.className = `result-message${type ? " " + type : ""}`;
  message.textContent = text;
  $("result").append(message);
  return message;
}

function showError(text) {
  $("prog").classList.add("show", "error");
  $("pstate").textContent = "ERRO";
  $("result").replaceChildren();
  resultMessage(text, "error");
  finishProcessing("ERRO");
}

window.api.onProgress((message) => setProg(Math.max(2, message.frac * 100), message.stage));
window.api.onWarning((message) => { lastWarning = message.message; });
window.api.onError((message) => showError(message.message + (message.detail ? " — " + message.detail : "")));
window.api.onDone((message) => {
  setProg(100, "Clips prontos e salvos no computador.");
  $("pstate").textContent = "CONCLUÍDO";
  $("result").replaceChildren();
  if (lastWarning) resultMessage(lastWarning, "warning");

  const cost = message.cost || {};
  const clipCount = (message.clips || []).length;
  resultMessage(
    `${clipCount} ${clipCount === 1 ? "clip salvo" : "clips salvos"} · $${Number(cost.cost_usd || 0).toFixed(4)} · ${Number(cost.total_tokens || 0).toLocaleString("pt-BR")} tokens.`,
  );

  const actions = document.createElement("div");
  actions.className = "result-actions";
  const libraryButton = document.createElement("button");
  libraryButton.className = "primary-button";
  libraryButton.textContent = "VER BIBLIOTECA";
  libraryButton.addEventListener("click", () => setView("biblioteca"));
  const folderButton = document.createElement("button");
  folderButton.className = "secondary-button";
  folderButton.textContent = "ABRIR PASTA";
  folderButton.addEventListener("click", () => window.api.openFolder(message.out));
  actions.append(libraryButton, folderButton);
  $("result").append(actions);

  if (message.totals) {
    $("costTotal").textContent = "$" + Number(message.totals.totalCost || 0).toFixed(4);
    $("costTokens").textContent = Number(message.totals.totalTokens || 0).toLocaleString("pt-BR");
  }
  finishProcessing("PRONTO");
});

async function loadLibrary() {
  libraryClips = await window.api.listClips();
  $("libCount").textContent = `${libraryClips.length} ${libraryClips.length === 1 ? "ARQUIVO" : "ARQUIVOS"}`;

  if (!libraryClips.length) {
    $("lib").innerHTML = `
      <div class="empty-state">
        <div>
          <span>BIBLIOTECA VAZIA</span>
          <h3>SEUS CLIPS APARECEM AQUI.</h3>
          <p>Volte ao Início, selecione um gameplay e gere o primeiro projeto local.</p>
        </div>
      </div>`;
    return;
  }

  $("lib").innerHTML = `<div class="clip-grid">${libraryClips.map(clipCard).join("")}</div>`;
  $("lib").querySelectorAll("video").forEach((video) => {
    const wrap = video.closest(".clip-wrap");
    wrap.addEventListener("mouseenter", () => {
      if (video.paused && video.muted) video.play().catch(() => {});
    });
    wrap.addEventListener("mouseleave", () => {
      if (!video.muted) return;
      video.pause();
      try { video.currentTime = 0.4; } catch { /* arquivo ainda carregando */ }
    });
  });
}

function clipCard(clip, index) {
  const score = clip.virality_score != null
    ? `<span class="clip-viral">SCORE ${Math.round(clip.virality_score)}</span>`
    : "";
  const duration = clip.duration_s != null
    ? `<span class="clip-duration">${Math.round(clip.duration_s)}S</span>`
    : "";
  const title = (clip.hook || "").trim() || clip.file;
  const description = (clip.description || "").trim();

  return `
    <article class="clip-card">
      <div class="clip-wrap">
        <video src="${escapeAttr(clip.url)}#t=0.4" muted loop playsinline controls preload="metadata"></video>
        <div class="clip-badges">${score}${duration}</div>
      </div>
      <div class="clip-body">
        <div class="clip-hook">${escapeHtml(title)}</div>
        ${description ? `<p class="clip-description">${escapeHtml(description)}</p>` : ""}
        <div class="clip-actions">
          <button type="button" data-action="open" data-index="${index}">ABRIR</button>
          <button type="button" data-action="copy" data-index="${index}" ${description ? "" : "disabled"}>COPIAR TEXTO</button>
        </div>
      </div>
    </article>`;
}

$("lib").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const clip = libraryClips[Number(button.dataset.index)];
  if (!clip) return;

  if (button.dataset.action === "open") {
    await window.api.openFolder(clip.path);
  } else if (button.dataset.action === "copy" && clip.description) {
    await navigator.clipboard.writeText(clip.description);
    button.textContent = "COPIADO";
    setTimeout(() => { button.textContent = "COPIAR TEXTO"; }, 1400);
  }
});

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function escapeAttr(value) {
  return escapeHtml(value);
}

$("refresh").addEventListener("click", loadLibrary);
$("openLib").addEventListener("click", () => window.api.openFolder(null));

updateSummary();
loadStats();
