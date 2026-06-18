"use client";

import { useEffect, useState } from "react";

const OPTS = ["LAYOUT: FACECAM", "LEGENDA: KARAOKÊ", "DURAÇÃO: 60–180s", "VIRAL: LLM"];

type Job = {
  id: string;
  source_url: string;
  status: string;
  progress: number;
  stage: string | null;
  error: string | null;
  created_at: string;
};

const STATUS_LABEL: Record<string, string> = {
  queued: "NA FILA",
  processing: "PROCESSANDO",
  done: "PRONTO",
  error: "ERRO",
};

export default function GerarPage() {
  const [url, setUrl] = useState("");
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [creating, setCreating] = useState(false);

  async function loadJobs() {
    const r = await fetch("/api/jobs");
    if (r.ok) setJobs((await r.json()).jobs);
  }

  useEffect(() => {
    loadJobs();
    // enquanto houver job ativo, atualiza o progresso
    const t = setInterval(loadJobs, 4000);
    return () => clearInterval(t);
  }, []);

  async function gerar(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setMsg(null);
    const r = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      setMsg({ kind: "ok", text: "Job criado! Está na fila — o processamento começa em instantes." });
      setUrl("");
      await loadJobs();
    } else {
      setMsg({ kind: "err", text: data.error ?? "Falhou ao criar o job." });
    }
    setCreating(false);
  }

  return (
    <div>
      <div className="badge">GERAR CLIPS</div>

      <form onSubmit={gerar} className="box panel-card">
        <label className="input">
          <span aria-hidden>🔗</span>
          <input
            placeholder="Cole o link do vídeo de gameplay..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <div className="opts">
          {OPTS.map((o) => (
            <span className="chip" key={o}>
              {o}
            </span>
          ))}
        </div>
        {msg && <p className={msg.kind === "ok" ? "dash-note" : "msg"}>{msg.text}</p>}
        <button
          className="btn"
          style={{ alignSelf: "flex-start" }}
          type="submit"
          disabled={creating || url.trim().length < 8}
        >
          {creating ? "..." : "GERAR CLIPS →"}
        </button>
      </form>

      <p className="hint">
        A geração roda no nosso servidor com a <b>sua chave</b>. O worker (Fase 3)
        ainda está sendo conectado — o job entra na fila e processa quando ele subir.
      </p>

      <div className="badge" style={{ marginTop: 36 }}>
        SEUS JOBS
      </div>
      {!jobs || jobs.length === 0 ? (
        <div className="empty">Nenhum job ainda — cole um link e gere. 🎮</div>
      ) : (
        <div className="jobs">
          {jobs.map((j) => (
            <div className="box job-row" key={j.id}>
              <div className="job-url">{j.source_url}</div>
              <div className={`job-badge job-${j.status}`}>
                {STATUS_LABEL[j.status] ?? j.status}
                {j.status === "processing" && ` · ${Math.round(j.progress * 100)}%`}
              </div>
              {j.error && <div className="job-err">{j.error}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
