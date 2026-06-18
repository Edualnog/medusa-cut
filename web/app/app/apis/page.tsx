"use client";

import { useEffect, useState } from "react";

type Status = { hasKey: boolean; last4: string | null; updatedAt: string | null };

export default function ApisPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    const r = await fetch("/api/keys");
    if (r.ok) setStatus(await r.json());
  }
  useEffect(() => {
    load();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    const r = await fetch("/api/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      setMsg({ kind: "ok", text: "Chave salva com segurança ✓" });
      setKey("");
      await load();
    } else {
      setMsg({ kind: "err", text: data.error ?? "Falhou ao salvar." });
    }
    setSaving(false);
  }

  async function remove() {
    setSaving(true);
    setMsg(null);
    await fetch("/api/keys", { method: "DELETE" });
    await load();
    setSaving(false);
  }

  return (
    <div>
      <div className="badge">APIs · SUA CHAVE</div>

      <div className="box panel-card">
        <p className="dash-list" style={{ margin: 0 }}>
          Conecte sua <b>chave da OpenRouter</b>. Você paga o custo da IA direto pra
          OpenRouter (centavos por vídeo) — por isso a Zorothax é mais barata, sem
          créditos inflados.
        </p>

        {status?.hasKey && (
          <div className="key-status">
            <span className="dot-on" /> CONECTADA · ····{status.last4}
            <button className="link-btn" onClick={remove} disabled={saving}>
              remover
            </button>
          </div>
        )}

        <form onSubmit={save} style={{ display: "contents" }}>
          <label className="field" style={{ margin: 0 }}>
            <span>{status?.hasKey ? "TROCAR CHAVE" : "OPENROUTER API KEY"}</span>
            <input
              type="password"
              placeholder="sk-or-v1-..."
              value={key}
              onChange={(e) => setKey(e.target.value)}
              autoComplete="off"
            />
          </label>
          {msg && <p className={msg.kind === "ok" ? "dash-note" : "msg"}>{msg.text}</p>}
          <button
            className="btn"
            style={{ alignSelf: "flex-start" }}
            type="submit"
            disabled={saving || key.trim().length < 10}
          >
            {saving ? "..." : "SALVAR CHAVE →"}
          </button>
        </form>
      </div>

      <p className="hint">
        🔒 Guardada <b>criptografada</b> (AES-256) e protegida por RLS — nunca volta
        pro navegador, só os 4 últimos dígitos. Só o nosso motor (no servidor) a usa
        pra gerar seus cortes.
      </p>
    </div>
  );
}
