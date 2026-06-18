// Logica da UI (arquivo externo — CSP nao permite script inline).
let mode = "file";
let filePath = null;

const $ = (id) => document.getElementById(id);

function refreshGen() {
  const ok = mode === "file" ? !!filePath : $("linkInput").value.trim().length > 6;
  $("gen").disabled = !ok;
}

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    mode = t.dataset.mode;
    $("srcFile").classList.toggle("hidden", mode !== "file");
    $("srcLink").classList.toggle("hidden", mode !== "link");
    refreshGen();
  };
});

$("srcFile").onclick = async () => {
  const p = await window.api.pickFile();
  if (p) {
    filePath = p;
    $("fileName").textContent = p.split("/").pop();
    $("fileName").classList.remove("ph");
  }
  refreshGen();
};
$("linkInput").oninput = refreshGen;
$("clips").oninput = (e) => ($("clipsN").textContent = e.target.value);

window.api.getKey().then((k) => {
  if (k) $("key").value = k;
});
$("key").onchange = () => window.api.setKey($("key").value.trim());

$("gen").onclick = () => {
  const key = $("key").value.trim();
  if (!key) {
    showError("Cole a sua chave da OpenRouter primeiro.");
    return;
  }
  window.api.setKey(key);
  const [minLen, maxLen] = $("dur").value.split(",").map(Number);
  const source = mode === "file" ? filePath : $("linkInput").value.trim();
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
};

function startUI() {
  $("prog").classList.add("show");
  $("gen").disabled = true;
  $("pstate").textContent = "PROCESSANDO";
  $("result").innerHTML = "";
  setProg(2, "Iniciando…");
}
function setProg(pct, stage) {
  $("pfill").style.width = pct + "%";
  $("ppct").textContent = Math.round(pct) + "%";
  if (stage) $("pstage").textContent = stage;
}
function showError(text) {
  $("prog").classList.add("show");
  $("pstate").textContent = "ERRO";
  $("result").innerHTML = '<div class="msg err">⚠ ' + text + "</div>";
  $("gen").disabled = false;
  refreshGen();
}

window.api.onProgress((m) => setProg(Math.max(2, m.frac * 100), m.stage));
window.api.onError((m) => showError(m.message + (m.detail ? " — " + m.detail : "")));
window.api.onDone((m) => {
  setProg(100, "Pronto!");
  $("pstate").textContent = "PRONTO";
  let html = "";
  (m.clips || []).forEach((c) => {
    const dur = Math.round(c.duration_s || 0);
    const score = c.virality_score != null ? "★ " + Math.round(c.virality_score) + " · " : "";
    html +=
      '<div class="clip"><div class="hook">' +
      (c.hook || c.file) +
      '</div><div class="meta">' +
      score +
      dur +
      "s · " +
      c.file +
      "</div></div>";
  });
  html += '<div class="row"><button class="btn2" id="openOut">ABRIR PASTA DOS CORTES</button></div>';
  $("result").innerHTML = html;
  document.getElementById("openOut").onclick = () => window.api.openFolder(m.out);
  $("gen").disabled = false;
  refreshGen();
});
