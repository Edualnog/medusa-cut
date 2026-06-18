"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ClipCard, type Clip } from "./clip-card";
import { Icon } from "./icons";

type Job = {
  id: string;
  source_url: string;
  status: string;
  progress: number;
  stage: string | null;
  error: string | null;
};

type Stats = { clipsTotal: number; jobsDone: number; costUsd: number; totalTokens: number };

const LAYOUTS: Record<string, string> = {
  facecam_top_gameplay_bottom: "Facecam em cima + gameplay",
  dynamic_gameplay: "Gameplay (segue a ação)",
  gameplay_blur: "Tela cheia + fundo desfocado",
  gameplay_only: "Crop central",
};
const DUR: Record<string, [number, number, string]> = {
  auto: [15, 90, "Auto (15–90s)"],
  curto: [10, 40, "Curtos (10–40s)"],
  longo: [60, 180, "Longos (60–180s)"],
};
const FACECAM: Record<string, string> = {
  auto: "Auto (rosto)",
  tr: "Topo direita",
  tl: "Topo esquerda",
  br: "Baixo direita",
  bl: "Baixo esquerda",
};
const FEATURES = [
  { icon: "spark", label: "GANCHO IA" },
  { icon: "cc", label: "LEGENDA KARAOKÊ" },
  { icon: "crop", label: "REENQUADRAR IA" },
  { icon: "chart", label: "ANÁLISE VIRAL" },
  { icon: "script", label: "DESCRIÇÃO IA" },
  { icon: "face", label: "FACECAM AUTO" },
];

export default function PainelPage() {
  const [url, setUrl] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [clipsById, setClipsById] = useState<Map<string, Clip>>(new Map());
  const [stats, setStats] = useState<Stats>({ clipsTotal: 0, jobsDone: 0, costUsd: 0, totalTokens: 0 });
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const hadActive = useRef(false);
  const [layout, setLayout] = useState("facecam_top_gameplay_bottom");
  const [durPreset, setDurPreset] = useState("auto");
  const [maxClips, setMaxClips] = useState(6);
  const [captions, setCaptions] = useState(true);
  const [facecamCorner, setFacecamCorner] = useState("auto");

  const loadClips = useCallback(async () => {
    const r = await fetch("/api/clips");
    if (!r.ok) return;
    const d = await r.json();
    setStats(d.stats);
    setClipsById((prev) => {
      const next = new Map(prev);
      let changed = false;
      for (const c of d.clips as Clip[]) {
        if (!next.has(c.id)) {
          next.set(c.id, c);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, []);

  const loadJobs = useCallback(async () => {
    const r = await fetch("/api/jobs");
    if (!r.ok) return;
    const list: Job[] = (await r.json()).jobs;
    setJobs(list);
    const active = list.some((j) => j.status === "queued" || j.status === "processing");
    if (hadActive.current && !active) loadClips();
    hadActive.current = active;
  }, [loadClips]);

  useEffect(() => {
    loadClips();
    loadJobs();
    const t = setInterval(loadJobs, 4000);
    return () => clearInterval(t);
  }, [loadClips, loadJobs]);

  async function gerar(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setMsg(null);
    const [min_len, max_len] = DUR[durPreset];
    const options = {
      layout,
      captions,
      max_clips: maxClips,
      min_len,
      max_len,
      facecam_auto: facecamCorner === "auto",
      facecam_corner: facecamCorner === "auto" ? null : facecamCorner,
      score_virality: true,
    };
    const r = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, options }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      setMsg({ kind: "ok", text: "Job criado! Está na fila — começa já." });
      setUrl("");
      await loadJobs();
    } else {
      setMsg({ kind: "err", text: data.error ?? "Falhou ao criar o job." });
    }
    setCreating(false);
  }

  const recent = [...clipsById.values()]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6);
  const active = jobs.find((j) => j.status === "queued" || j.status === "processing");
  const failed = jobs.find((j) => j.status === "error");

  return (
    <div className="painel2">
      {/* top bar */}
      <div className="top2">
        <span className="top2-title">INÍCIO</span>
        <div className="top2-right">
          <span className="top2-chip" title="Gasto de IA na sua chave OpenRouter">
            <Icon name="coin" size={15} /> ${stats.costUsd.toFixed(4)}
          </span>
          <span className="top2-chip">
            <Icon name="film" size={15} /> {stats.clipsTotal}
          </span>
        </div>
      </div>

      {/* hero: gerar */}
      <form onSubmit={gerar} className="gen2 box">
        <label className="gen2-input">
          <span aria-hidden><Icon name="link" size={20} /></span>
          <input
            placeholder="Cole o link do seu vídeo de gameplay aqui..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>

        <div className="opts-row gen2-opts">
          <label className="opt">
            <span>ESTILO / LAYOUT</span>
            <select value={layout} onChange={(e) => setLayout(e.target.value)}>
              {Object.entries(LAYOUTS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>
          <label className="opt">
            <span>DURAÇÃO</span>
            <select value={durPreset} onChange={(e) => setDurPreset(e.target.value)}>
              {Object.entries(DUR).map(([v, d]) => (
                <option key={v} value={v}>{d[2]}</option>
              ))}
            </select>
          </label>
          {layout === "facecam_top_gameplay_bottom" && (
            <label className="opt">
              <span>FACECAM</span>
              <select value={facecamCorner} onChange={(e) => setFacecamCorner(e.target.value)}>
                {Object.entries(FACECAM).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
          )}
          <label className="opt">
            <span>Nº DE CORTES: {maxClips}</span>
            <input type="range" min={1} max={10} value={maxClips} onChange={(e) => setMaxClips(Number(e.target.value))} />
          </label>
          <label className="opt opt-check">
            <input type="checkbox" checked={captions} onChange={(e) => setCaptions(e.target.checked)} />
            <span>Legenda karaokê</span>
          </label>
        </div>

        <button className="gen2-btn" type="submit" disabled={creating || url.trim().length < 8}>
          {creating ? "..." : "✦  OBTER CLIPES EM 1 CLIQUE  ✦"}
        </button>
        <p className="gen2-hint">ⓘ Suporta YouTube, TikTok e muito mais — processa na nuvem com a sua chave.</p>
      </form>
      {msg && <p className={msg.kind === "ok" ? "dash-note" : "msg"} style={{ textAlign: "center" }}>{msg.text}</p>}

      {/* vitrine de features (reais) */}
      <div className="feat2">
        {FEATURES.map((f) => (
          <div className="feat2-item" key={f.label}>
            <div className="feat2-icon"><Icon name={f.icon} size={26} /></div>
            <div className="feat2-label">{f.label}</div>
          </div>
        ))}
      </div>

      {/* job ativo */}
      {active && (
        <div className="box job-active">
          <div className="job-active-top">
            <span>{active.status === "queued" ? "NA FILA" : "PROCESSANDO"}</span>
            <span>{Math.round(active.progress * 100)}%</span>
          </div>
          <div className="progress">
            <div className="progress-fill" style={{ width: `${Math.max(2, active.progress * 100)}%` }} />
          </div>
          <div className="job-stage">{active.stage ?? "Aguardando o worker pegar o job…"}</div>
        </div>
      )}
      {failed && !active && <div className="box job-failed">⚠ Último job falhou: {failed.error}</div>}

      {/* clipes */}
      <div className="painel-section recent-head">
        <div className="badge">SEUS CLIPES ({stats.clipsTotal})</div>
        <Link href="/app/biblioteca" className="nav-link recent-all">VER TUDO →</Link>
      </div>
      {recent.length === 0 ? (
        <div className="empty">Nenhum clip ainda — cole um link e gere. 🎮</div>
      ) : (
        <div className="clip-grid">
          {recent.map((c) => (
            <ClipCard key={c.id} clip={c} />
          ))}
        </div>
      )}

      {/* stats */}
      <div className="box stats-bar">
        <div className="stat">
          <span className="stat-label">VÍDEOS ANALISADOS</span>
          <span className="stat-val">{stats.jobsDone}</span>
        </div>
        <div className="stat">
          <span className="stat-label">TOTAL DE CLIPS</span>
          <span className="stat-val">{stats.clipsTotal}</span>
        </div>
        <div className="stat">
          <span className="stat-label">💸 GASTO DE IA</span>
          <span className="stat-val">${stats.costUsd.toFixed(4)}</span>
          <span className="stat-sub">{stats.totalTokens.toLocaleString("pt-BR")} tokens</span>
        </div>
      </div>
    </div>
  );
}
