"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ClipCard, type Clip } from "./clip-card";
import { Icon } from "./icons";
import { createClient } from "@/lib/supabase/client";

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
// PUT do arquivo direto no R2, com progresso (XHR — fetch nao reporta upload).
function putWithProgress(
  url: string,
  file: File,
  contentType: string,
  onPct: (p: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", contentType);
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) onPct(Math.round((ev.loaded / ev.total) * 100));
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`Falha no upload (HTTP ${xhr.status}).`));
    xhr.onerror = () => reject(new Error("Erro de rede no upload."));
    xhr.send(file);
  });
}

export default function PainelPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadPct, setUploadPct] = useState<number | null>(null);
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

    const supabase = createClient();
    let channel: ReturnType<typeof supabase.channel> | null = null;

    // Realtime: o worker escreve progresso/stage no job e insere os clips ->
    // a UI reage na hora (sem polling). RLS garante que so vem o do proprio user.
    supabase.auth.getUser().then(({ data }) => {
      const uid = data.user?.id;
      if (!uid) return;
      channel = supabase
        .channel("painel")
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "jobs", filter: `user_id=eq.${uid}` },
          (payload) => {
            const row = payload.new as Job;
            if (!row?.id) return;
            setJobs((prev) => {
              const i = prev.findIndex((j) => j.id === row.id);
              if (i === -1) return [row, ...prev];
              const next = [...prev];
              next[i] = { ...next[i], ...row };
              return next;
            });
            if (row.status === "done" || row.status === "error") loadClips();
          },
        )
        .on(
          "postgres_changes",
          { event: "INSERT", schema: "public", table: "clips", filter: `user_id=eq.${uid}` },
          () => loadClips(),
        )
        .subscribe();
    });

    // rede de seguranca: se o realtime cair, ainda reconcilia de vez em quando.
    const t = setInterval(loadJobs, 20000);
    return () => {
      clearInterval(t);
      if (channel) supabase.removeChannel(channel);
    };
  }, [loadClips, loadJobs]);

  async function gerar(e: React.FormEvent) {
    e.preventDefault();
    if (!file || creating) return;
    setCreating(true);
    setMsg(null);
    const ct = file.type || "video/mp4";
    try {
      // 1. pede a URL assinada de upload (valida formato/tamanho + BYO key)
      const up = await fetch("/api/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contentType: ct, size: file.size }),
      });
      const upData = await up.json().catch(() => ({}));
      if (!up.ok) throw new Error(upData.error ?? "Falha ao preparar o upload.");

      // 2. sobe o arquivo direto pro R2 (com barra de progresso)
      await putWithProgress(upData.uploadUrl, file, ct, setUploadPct);

      // 3. cria o job apontando pra chave do upload
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
        body: JSON.stringify({ upload_key: upData.key, options }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error ?? "Falhou ao criar o job.");

      setMsg({ kind: "ok", text: "Vídeo enviado! Está na fila — começa já." });
      setFile(null);
      await loadJobs();
    } catch (err) {
      setMsg({ kind: "err", text: err instanceof Error ? err.message : "Erro inesperado." });
    } finally {
      setUploadPct(null);
      setCreating(false);
    }
  }

  const recent = [...clipsById.values()]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6);
  const active = jobs.find((j) => j.status === "queued" || j.status === "processing");
  const failed = jobs.find((j) => j.status === "error");
  const perClip = stats.clipsTotal > 0 ? stats.costUsd / stats.clipsTotal : 0;

  return (
    <div className="painel2">
      {/* top bar */}
      <div className="top2">
        <span className="top2-title">INICIO</span>
        <div className="top2-right">
          <span className="top2-chip" title="Total de clipes gerados">
            <Icon name="film" size={15} /> {stats.clipsTotal} clipes
          </span>
        </div>
      </div>

      {/* hero: gerar */}
      <form onSubmit={gerar} className="gen2 box">
        <div className="gen2-bar">
          <label className="gen2-input gen2-file">
            <span aria-hidden><Icon name="film" size={20} /></span>
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/webm,video/x-matroska"
              hidden
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <span className={file ? "gen2-filename" : "gen2-filename gen2-placeholder"}>
              {file ? file.name : "Escolha o vídeo do seu gameplay (MP4/MOV)…"}
            </span>
          </label>
          <button className="gen2-btn" type="submit" disabled={creating || !file}>
            {creating ? (uploadPct != null ? `${uploadPct}%` : "...") : "✦ GERAR"}
          </button>
        </div>

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

        <p className="gen2-hint">ⓘ Suba o seu gameplay (MP4/MOV até 2 GB) — processa na nuvem com a sua chave.</p>
      </form>
      {msg && <p className={msg.kind === "ok" ? "dash-note" : "msg"} style={{ textAlign: "center" }}>{msg.text}</p>}

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
        <div className="empty">Nenhum clip ainda — cole um link e gere.</div>
      ) : (
        <div className="clip-grid">
          {recent.map((c) => (
            <ClipCard key={c.id} clip={c} />
          ))}
        </div>
      )}

      {/* custo de IA — o diferencial: você paga só a IA, na sua chave, sem markup */}
      <div className="box cost-card">
        <div className="cost-head">
          <Icon name="coin" size={14} />
          <span>CUSTO DE IA · SUA CHAVE OPENROUTER</span>
        </div>
        <div className="cost-metrics">
          <div className="cost-metric">
            <span className="cost-val">${stats.costUsd.toFixed(4)}</span>
            <span className="cost-label">TOTAL GASTO</span>
          </div>
          <div className="cost-metric cost-hero">
            <span className="cost-val">${perClip.toFixed(4)}</span>
            <span className="cost-label">MEDIA / CORTE</span>
          </div>
          <div className="cost-metric">
            <span className="cost-val">{stats.totalTokens.toLocaleString("pt-BR")}</span>
            <span className="cost-label">TOKENS</span>
          </div>
        </div>
        <p className="cost-note">
          ⓘ Você paga só a IA, direto na sua chave — sem markup nosso.
        </p>
      </div>
    </div>
  );
}
