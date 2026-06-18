"use client";

// SPIKE 2 (dev tool): mede o decode com WebCodecs (sequencial, acelerado por
// hardware) + calculo de motion. Decide se o "proxy 2 fases" no navegador e viavel.
// /spike — escolha o arquivo, clique ANALISAR, me mande os numeros.

import { useRef, useState } from "react";

type Line = { t: string; kind?: "ok" | "err" | "info" };

export default function SpikePage() {
  const [lines, setLines] = useState<Line[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const stopRef = useRef(false);

  const add = (t: string, kind?: Line["kind"]) => {
    // eslint-disable-next-line no-console
    console.log("[spike]", t);
    setLines((l) => [...l, { t, kind }]);
  };

  async function run() {
    if (!file || busy) return;
    setBusy(true);
    setLines([]);
    stopRef.current = false;
    add(`Arquivo: ${file.name} — ${(file.size / 1e9).toFixed(2)} GB`);

    if (typeof window === "undefined" || !("VideoDecoder" in window)) {
      add("Este navegador NÃO tem WebCodecs (VideoDecoder).", "err");
      setBusy(false);
      return;
    }

    const mod: any = await import("mp4box");
    const MP4Box = mod.default ?? mod;
    const DataStream = mod.DataStream;

    const mp4 = MP4Box.createFile();
    const CAP = 3000; // mede nos primeiros 3000 frames
    let decoded = 0;
    let queued = 0;
    let t0 = 0;
    let track: any = null;
    let decoder: VideoDecoder | null = null;

    const cw = 320;
    let ch = 180;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
    let prev: Uint8ClampedArray | null = null;
    let motionSum = 0;

    function description(f: any, trk: any): Uint8Array | undefined {
      const t = f.getTrackById(trk.id);
      for (const e of t.mdia.minf.stbl.stsd.entries) {
        const box = e.avcC || e.hvcC || e.vpcC || e.av1C;
        if (box) {
          const ds = new DataStream(undefined, 0, DataStream.BIG_ENDIAN);
          box.write(ds);
          return new Uint8Array(ds.buffer, 8); // tira o header de 8 bytes
        }
      }
      return undefined;
    }

    function finish(reason: string) {
      if (stopRef.current) return;
      stopRef.current = true;
      const el = (performance.now() - t0) / 1000;
      const rate = decoded / Math.max(0.001, el);
      add(`✅ ${decoded} frames decodificados em ${el.toFixed(1)}s → ${rate.toFixed(0)} fps (${reason})`, "ok");
      if (track) {
        const durMin = track.movie_duration / track.movie_timescale / 60;
        const totalFrames = durMin * 60 * (track.video?.fps ?? 60);
        add(`Projeção: decodificar o vídeo inteiro (~${(totalFrames / 1000).toFixed(0)}k frames) ≈ ${(totalFrames / rate / 60).toFixed(1)} min`, "ok");
      }
      add(`Motion calculado junto ✓ (soma relativa ${(motionSum).toFixed(0)})`, "ok");
      try { decoder?.close(); } catch { /* ignore */ }
      setBusy(false);
    }

    mp4.onError = (e: any) => { add("mp4box erro: " + e, "err"); finish("erro"); };

    mp4.onReady = (info: any) => {
      track = info.videoTracks[0];
      if (!track) { add("nenhuma trilha de vídeo encontrada", "err"); finish("sem video"); return; }
      const durMin = info.duration / info.timescale / 60;
      add(`codec: ${track.codec} · ${track.video.width}x${track.video.height} · ${durMin.toFixed(1)} min`, "ok");
      ch = Math.max(1, Math.round((cw * track.video.height) / track.video.width));
      canvas.width = cw; canvas.height = ch;

      decoder = new VideoDecoder({
        output: (frame) => {
          if (decoded === 0) t0 = performance.now();
          decoded++;
          ctx.drawImage(frame, 0, 0, cw, ch);
          frame.close();
          const data = ctx.getImageData(0, 0, cw, ch).data;
          if (prev) {
            let s = 0;
            for (let p = 0; p < data.length; p += 16) s += Math.abs(data[p] - prev[p]);
            motionSum += s;
          }
          prev = data;
          if (decoded % 500 === 0) {
            const el = (performance.now() - t0) / 1000;
            add(`…${decoded} frames · ${(decoded / el).toFixed(0)} fps`, "info");
          }
          if (decoded >= CAP) finish("amostra de " + CAP);
        },
        error: (e) => { add("decoder erro: " + e.message, "err"); finish("erro decoder"); },
      });

      const desc = description(mp4, track);
      if (!desc) { add("não achei a descrição do codec (avcC) — formato incomum", "err"); finish("sem avcC"); return; }
      decoder.configure({
        codec: track.codec,
        codedWidth: track.video.width,
        codedHeight: track.video.height,
        description: desc,
      });
      mp4.setExtractionOptions(track.id, null, { nbSamples: 500 });
      mp4.start();
      add("Decodificando (WebCodecs)…", "info");
    };

    mp4.onSamples = (_id: number, _user: any, samples: any[]) => {
      for (const s of samples) {
        if (stopRef.current || queued >= CAP) return;
        queued++;
        decoder!.decode(new EncodedVideoChunk({
          type: s.is_sync ? "key" : "delta",
          timestamp: (s.cts * 1e6) / s.timescale,
          duration: (s.duration * 1e6) / s.timescale,
          data: s.data,
        }));
      }
    };

    // alimenta o arquivo em pedaços de 16MB (nao carrega 2.8GB de uma vez)
    add("Demuxando…", "info");
    const CHUNK = 1 << 24;
    let offset = 0;
    try {
      while (offset < file.size && !stopRef.current && queued < CAP) {
        const buf: any = await file.slice(offset, offset + CHUNK).arrayBuffer();
        buf.fileStart = offset;
        mp4.appendBuffer(buf);
        offset += CHUNK;
        await new Promise((r) => setTimeout(r, 0)); // deixa o decoder respirar
      }
      mp4.flush();
    } catch (e) {
      add("falha ao ler/demuxar: " + (e as Error).message, "err");
      finish("erro leitura");
    }
  }

  return (
    <div style={{ maxWidth: 820, margin: "40px auto", padding: 24, fontFamily: "monospace", color: "#eee", background: "#0a0a0d", minHeight: "100vh" }}>
      <h1 style={{ fontSize: 18 }}>SPIKE 2 · WebCodecs no navegador</h1>
      <p style={{ color: "#9aa0a6", fontSize: 13 }}>
        Mede o decode acelerado por hardware (mp4box + VideoDecoder) + motion. Local no Chrome, nada sobe.
        Escolha o arquivo, clique ANALISAR, me mande os números. Console (F12) tem o log cru.
      </p>
      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "12px 0" }}>
        <input type="file" accept="video/*" disabled={busy}
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setLines([]); }} />
        <button onClick={run} disabled={!file || busy}
          style={{ padding: "8px 18px", background: file && !busy ? "#ffd11a" : "#333", color: file && !busy ? "#000" : "#888", border: "none", cursor: file && !busy ? "pointer" : "default", fontFamily: "monospace", fontWeight: "bold" }}>
          {busy ? "ANALISANDO…" : "ANALISAR"}
        </button>
      </div>
      <div style={{ marginTop: 16, fontSize: 13, lineHeight: 1.6 }}>
        {lines.map((l, i) => (
          <div key={i} style={{ color: l.kind === "err" ? "#ff6b6b" : l.kind === "ok" ? "#ffd11a" : l.kind === "info" ? "#9aa0a6" : "#eee" }}>{l.t}</div>
        ))}
        {busy && <div style={{ color: "#9aa0a6" }}>…rodando…</div>}
      </div>
    </div>
  );
}
