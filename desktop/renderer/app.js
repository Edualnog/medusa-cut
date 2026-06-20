// Interface do app desktop. Toda integracao nativa passa pela ponte segura do preload.
const $ = (id) => document.getElementById(id);

const VIEW_META = {
  inicio: { title: "INÍCIO", code: "01" },
  biblioteca: { title: "BIBLIOTECA", code: "02" },
  apis: { title: "CHAVES API", code: "03" },
  conta: { title: "CONTA", code: "04" },
};

const LAYOUT_LABELS = {
  facecam_top_gameplay_bottom: "FACECAM + GAMEPLAY",
  dynamic_gameplay: "SEGUE A AÇÃO",
  gameplay_blur: "FUNDO DESFOCADO",
};

const DURATION_LABELS = {
  "60,180": "PADRÃO · 1–3MIN",
  "120,300": "LONGOS · 2–5MIN",
  "30,90": "CURTOS · 30–90S",
};

let mode = "file";
let filePath = null;
let isProcessing = false;
let lastWarning = "";
let libraryClips = [];
let linkPreviewData = null;
let linkPreviewTimer = null;
let linkPreviewRequest = 0;

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
  if (view === "conta") loadAccount();
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
  $("srcLinkGroup").classList.toggle("hidden", mode !== "link");
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

$("linkInput").addEventListener("input", queueLinkPreview);
$("layout").addEventListener("change", updateSummary);
$("dur").addEventListener("change", updateSummary);
$("facecam").addEventListener("change", updateSummary);
$("captions").addEventListener("change", updateSummary);
$("clips").addEventListener("input", updateSummary);

$("pasteLink").addEventListener("click", async () => {
  try {
    const clipboardText = await navigator.clipboard.readText();
    if (clipboardText.trim()) {
      $("linkInput").value = clipboardText.trim();
      $("linkInput").dispatchEvent(new Event("input", { bubbles: true }));
    }
  } catch {
    $("linkInput").focus();
  }
});

function validPublicUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function isYoutubeUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
    return ["youtu.be", "youtube.com", "m.youtube.com", "music.youtube.com"].includes(host);
  } catch {
    return false;
  }
}

function resetLinkPreview() {
  linkPreviewData = null;
  $("linkPreview").className = "link-preview hidden";
  $("linkPreviewImage").removeAttribute("src");
  $("linkPreviewImage").alt = "";
  $("linkPreviewTitle").textContent = "";
  $("linkPreviewAuthor").textContent = "";
  $("linkPreviewUrl").textContent = "";
}

function showLinkPreviewState(state, data = {}) {
  const preview = $("linkPreview");
  preview.className = `link-preview ${state}`.trim();

  if (state === "loading") {
    $("linkPreviewStatus").textContent = "YOUTUBE · ANALISANDO LINK";
    $("linkPreviewTitle").textContent = "Buscando informações do vídeo…";
    $("linkPreviewAuthor").textContent = "";
    $("linkPreviewUrl").textContent = "";
    return;
  }

  if (state === "error") {
    $("linkPreviewStatus").textContent = "PRÉVIA NÃO DISPONÍVEL";
    $("linkPreviewTitle").textContent = data.error || "Não foi possível identificar este vídeo.";
    $("linkPreviewAuthor").textContent = "Confira o link e tente novamente.";
    $("linkPreviewUrl").textContent = "";
    return;
  }

  const hasThumbnail = Boolean(data.thumbnail);
  preview.classList.toggle("no-image", !hasThumbnail);
  $("linkPreviewStatus").textContent = `${data.provider || "YOUTUBE"} · VÍDEO ENCONTRADO`;
  $("linkPreviewTitle").textContent = data.title;
  $("linkPreviewAuthor").textContent = data.authorName;
  $("linkPreviewUrl").textContent = data.canonicalUrl;
  if (hasThumbnail) {
    $("linkPreviewImage").src = data.thumbnail;
    $("linkPreviewImage").alt = `Miniatura do vídeo ${data.title}`;
  }
}

function queueLinkPreview() {
  const rawUrl = $("linkInput").value.trim();
  clearTimeout(linkPreviewTimer);
  linkPreviewRequest += 1;
  resetLinkPreview();
  updateSummary();

  if (!rawUrl) return;
  if (!validPublicUrl(rawUrl)) {
    showLinkPreviewState("error", { error: "COLE UM LINK COMPLETO, COMEÇANDO COM HTTPS://" });
    return;
  }
  if (!isYoutubeUrl(rawUrl)) return;

  const requestId = linkPreviewRequest;
  showLinkPreviewState("loading");
  linkPreviewTimer = setTimeout(async () => {
    let result;
    try {
      result = await window.api.getLinkPreview(rawUrl);
    } catch {
      result = { ok: false, error: "NÃO FOI POSSÍVEL CARREGAR A PRÉVIA" };
    }
    if (requestId !== linkPreviewRequest || $("linkInput").value.trim() !== rawUrl) return;

    if (result.unsupported) {
      resetLinkPreview();
      updateSummary();
      return;
    }

    if (!result.ok) {
      showLinkPreviewState("error", result);
      updateSummary();
      return;
    }

    linkPreviewData = { ...result, sourceUrl: rawUrl };
    showLinkPreviewState("ready", result);
    updateSummary();
  }, 450);
}

function sourceReady() {
  if (mode === "file") return Boolean(filePath);
  const sourceUrl = $("linkInput").value.trim();
  if (!validPublicUrl(sourceUrl)) return false;
  if (!isYoutubeUrl(sourceUrl)) return true;
  return linkPreviewData?.sourceUrl === sourceUrl;
}

function updateSummary() {
  const clips = Number($("clips").value);
  const selectedLayout = $("layout").value;
  const facecamLayout = selectedLayout === "facecam_top_gameplay_bottom";

  $("clipsN").textContent = `${clips} ${clips === 1 ? "CLIP" : "CLIPS"}`;
  $("summarySource").textContent = sourceReady()
    ? (mode === "file"
      ? $("fileName").textContent
      : (linkPreviewData?.sourceUrl === $("linkInput").value.trim() ? "YOUTUBE · CONFIRMADO" : "LINK PÚBLICO"))
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

// ---- Autenticação (gate) ----
let authMode = "login";

// Apos login/sessao: esconde o login e decide entre onboarding e app.
async function showApp(email) {
  $("authGate").classList.add("hidden");
  $("accountEmail").textContent = email || "";
  const ob = await window.api.getOnboarding();
  if (ob && ob.done) revealApp();
  else showOnboarding(ob);
}

function revealApp() {
  $("onboarding").classList.add("hidden");
  $("appShell").classList.remove("hidden");
  loadLibraryPath();
}

function showGate() {
  $("appShell").classList.add("hidden");
  $("onboarding").classList.add("hidden");
  $("authGate").classList.remove("hidden");
}

function setAuthMsg(text, isError = true) {
  const el = $("authMsg");
  el.textContent = text || "";
  el.classList.toggle("hidden", !text);
  el.classList.toggle("error", Boolean(text) && isError);
}

function authSubmitLabel() {
  return authMode === "login" ? "ENTRAR →" : "CRIAR CONTA →";
}

function setAuthMode(next) {
  authMode = next;
  $("authTitle").textContent = next === "login" ? "ENTRAR" : "CRIAR CONTA";
  $("authSubmit").textContent = authSubmitLabel();
  $("authSwitchText").textContent = next === "login" ? "Não tem conta?" : "Já tem conta?";
  $("authSwitch").textContent = next === "login" ? "Criar conta" : "Entrar";
  $("authPassword").setAttribute("autocomplete", next === "login" ? "current-password" : "new-password");
  setAuthMsg("");
}

$("authSwitch").addEventListener("click", () => {
  setAuthMode(authMode === "login" ? "signup" : "login");
});

$("forgotPass").addEventListener("click", async () => {
  const email = $("authEmail").value.trim();
  if (!email) {
    setAuthMsg("Digite seu e-mail acima para receber o link de redefinição.");
    return;
  }
  const btn = $("forgotPass");
  btn.disabled = true;
  const res = await window.api.recoverPassword(email);
  setAuthMsg(
    res && res.ok
      ? "Enviamos um link para seu e-mail. Abra-o para definir uma nova senha."
      : (res && res.error) || "Não foi possível enviar.",
    !(res && res.ok)
  );
  btn.disabled = false;
});

$("authForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = $("authEmail").value.trim();
  const password = $("authPassword").value;
  if (!email || password.length < 6) {
    setAuthMsg("Informe e-mail e senha (mínimo 6 caracteres).");
    return;
  }

  const submit = $("authSubmit");
  submit.disabled = true;
  submit.textContent = "...";
  setAuthMsg("");
  try {
    const res = authMode === "login"
      ? await window.api.signIn(email, password)
      : await window.api.signUp(email, password);

    if (res.ok && res.needsConfirm) {
      setAuthMode("login");
      setAuthMsg("Conta criada! Confirme o e-mail e depois entre.", false);
    } else if (res.ok) {
      $("authPassword").value = "";
      showApp(res.email || email);
    } else {
      setAuthMsg(res.error || "Não foi possível continuar.");
    }
  } finally {
    submit.disabled = false;
    submit.textContent = authSubmitLabel();
  }
});

$("signOut").addEventListener("click", async () => {
  await window.api.signOut();
  $("authEmail").value = "";
  $("authPassword").value = "";
  setAuthMode("login");
  showGate();
});

// Olhinho de mostrar/ocultar senha (qualquer campo dentro de .pass-row)
document.querySelectorAll(".pass-eye").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = btn.parentElement.querySelector("input");
    if (!input) return;
    const reveal = input.type === "password";
    input.type = reveal ? "text" : "password";
    btn.classList.toggle("showing", reveal);
    btn.setAttribute("aria-label", reveal ? "Ocultar senha" : "Mostrar senha");
  });
});

(async function initAuth() {
  const session = await window.api.getSession();
  if (session && session.email) showApp(session.email);
  else showGate();
})();

// ---- Modal de documentos legais ----
function openLegal(kind) {
  const legal = window.LEGAL || {};
  $("legalModalTitle").textContent = kind === "privacy" ? "POLÍTICA DE PRIVACIDADE" : "TERMOS DE USO";
  $("legalModalBody").innerHTML = (kind === "privacy" ? legal.privacy : legal.terms) || "<p>Documento indisponível.</p>";
  $("legalModalBody").scrollTop = 0;
  $("legalModal").classList.remove("hidden");
}
function closeLegal() {
  $("legalModal").classList.add("hidden");
}
$("legalClose").addEventListener("click", closeLegal);
$("legalModal").addEventListener("click", (e) => {
  if (e.target === $("legalModal")) closeLegal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("legalModal").classList.contains("hidden")) closeLegal();
});
// qualquer botao com data-legal abre o documento (onboarding + view de config)
document.querySelectorAll("[data-legal]").forEach((btn) => {
  btn.addEventListener("click", () => openLegal(btn.dataset.legal));
});

// ---- Onboarding (wizard de 3 passos) ----
let obLibraryDir = null;
let obDefaultDir = null;

function showOnboarding(ob) {
  obDefaultDir = (ob && ob.defaultDir) || null;
  obLibraryDir = (ob && ob.libraryDir) || null;
  $("onboarding").classList.remove("hidden");
  setObFolder(obLibraryDir);
  obGoToStep(1);
}

function obGoToStep(n) {
  [1, 2, 3].forEach((i) => {
    $("obStep" + i).classList.toggle("hidden", i !== n);
  });
  document.querySelectorAll(".ob-steps li").forEach((li) => {
    li.classList.toggle("active", Number(li.dataset.dot) <= n);
  });
}

function obAllAccepted() {
  return ["acTerms", "acPrivacy", "acContent", "acAge"].every((id) => $(id).checked);
}

function setObFolder(dir) {
  obLibraryDir = dir || null;
  $("obLibraryPath").textContent = obLibraryDir || (obDefaultDir ? `${obDefaultDir} (padrão)` : "Nenhuma pasta escolhida");
  $("obLibraryPath").classList.toggle("placeholder", !obLibraryDir);
  $("obFinish").disabled = !obLibraryDir;
}

document.querySelectorAll("[data-ob-next]").forEach((btn) => {
  btn.addEventListener("click", () => obGoToStep(Number(btn.dataset.obNext)));
});
document.querySelectorAll("[data-ob-back]").forEach((btn) => {
  btn.addEventListener("click", () => obGoToStep(Number(btn.dataset.obBack)));
});
document.querySelectorAll("[data-accept]").forEach((cb) => {
  cb.addEventListener("change", () => { $("obToStep3").disabled = !obAllAccepted(); });
});

$("obUseDefault").addEventListener("click", () => setObFolder(obDefaultDir));
$("obPickFolder").addEventListener("click", async () => {
  const dir = await window.api.pickLibraryDir();
  if (dir) setObFolder(dir);
});

$("obFinish").addEventListener("click", async () => {
  if (!obAllAccepted() || !obLibraryDir) return;
  $("obFinish").disabled = true;
  const res = await window.api.completeOnboarding({
    accepts: { terms: true, privacy: true, content: true, age: true },
    libraryDir: obLibraryDir,
  });
  if (res && res.ok) revealApp();
  else {
    $("obFinish").disabled = false;
    $("obFolderNote").textContent = (res && res.error) || "Não foi possível concluir.";
  }
});

// ---- Pasta dos clips na view de config ----
async function loadLibraryPath() {
  const info = await window.api.getLibraryDir();
  const path = (info && (info.dir || info.defaultDir)) || "—";
  const isDefault = info && !info.dir;
  $("cfgLibraryPath").textContent = isDefault ? `${path} (padrão)` : path;
}

$("cfgOpenFolder").addEventListener("click", () => window.api.openFolder(null));
$("cfgChangeFolder").addEventListener("click", async () => {
  const dir = await window.api.pickLibraryDir();
  if (!dir) return;
  const res = await window.api.setLibraryDir(dir);
  if (res && res.ok) loadLibraryPath();
});

// ---- Aba CONTA ----
async function loadAccount() {
  const acc = await window.api.getAccount();
  const email = (acc && acc.email) || "—";
  $("contaEmail").textContent = email;
  $("accountEmail").textContent = email !== "—" ? email : $("accountEmail").textContent;
}

$("resetPass").addEventListener("click", async () => {
  const btn = $("resetPass");
  btn.disabled = true;
  const res = await window.api.recoverPassword(); // sem email -> usa o da sessao
  const ok = Boolean(res && res.ok);
  $("resetPassNote").textContent = ok
    ? "EMAIL ENVIADO. ABRA O LINK NO NAVEGADOR PARA DEFINIR A NOVA SENHA."
    : (res && res.error) || "NÃO FOI POSSÍVEL ENVIAR.";
  $("resetPassNote").classList.toggle("error", !ok);
  btn.disabled = false;
});

function resetToLogin() {
  if ($("key")) $("key").value = "";
  $("authEmail").value = "";
  $("authPassword").value = "";
  setAuthMode("login");
  showGate();
}

$("wipeData").addEventListener("click", async () => {
  const ok = window.confirm(
    "Apagar a chave da OpenRouter, a sessão e as preferências deste dispositivo?\n\nOs clips já gerados NÃO serão apagados. Você precisará entrar e configurar novamente."
  );
  if (!ok) return;
  await window.api.wipeLocalData();
  resetToLogin();
});

$("deleteAccount").addEventListener("click", async () => {
  const ok = window.confirm(
    "Excluir sua conta permanentemente?\n\nEsta ação NÃO pode ser desfeita. Você perderá o acesso e seus dados locais serão apagados (os clips já gerados ficam no seu computador)."
  );
  if (!ok) return;
  const btn = $("deleteAccount");
  btn.disabled = true;
  $("deleteAccountNote").classList.remove("error");
  $("deleteAccountNote").textContent = "EXCLUINDO…";
  const res = await window.api.deleteAccount();
  if (res && res.ok) {
    resetToLogin();
  } else {
    btn.disabled = false;
    $("deleteAccountNote").textContent = (res && res.error) || "NÃO FOI POSSÍVEL EXCLUIR.";
    $("deleteAccountNote").classList.add("error");
  }
});

// --- Versão real (nunca hardcoded) + banner de auto-update.
window.api.getVersion().then((v) => {
  if (v) $("appVersion").textContent = "V" + v;
}).catch(() => {});

function showUpdateBanner(text, btnLabel, onClick) {
  const btn = $("updateBannerBtn");
  $("updateBannerText").textContent = text;
  if (btnLabel) {
    btn.textContent = btnLabel;
    btn.onclick = onClick;
    btn.classList.remove("hidden");
  } else {
    btn.classList.add("hidden");
  }
  $("updateBanner").classList.remove("hidden");
}

// Win/Linux: avisa -> baixa -> reinicia (fluxo "avisar antes de baixar").
window.api.onUpdateAvailable((m) => {
  showUpdateBanner(`NOVA VERSÃO V${m.version} DISPONÍVEL`, "BAIXAR", () => {
    showUpdateBanner("BAIXANDO ATUALIZAÇÃO… 0%", null);
    window.api.downloadUpdate();
  });
});
window.api.onUpdateProgress((m) => showUpdateBanner(`BAIXANDO ATUALIZAÇÃO… ${m.percent}%`, null));
window.api.onUpdateReady((m) =>
  showUpdateBanner(`V${m.version} PRONTA — REINICIE PRA INSTALAR`, "REINICIAR", () => window.api.installUpdate())
);
// macOS sem assinatura: não troca o binário no app -> manda baixar no site.
window.api.onUpdateSite((m) =>
  showUpdateBanner(`NOVA VERSÃO V${m.version} DISPONÍVEL`, "BAIXAR NO SITE", () => window.api.openDownloadPage())
);
