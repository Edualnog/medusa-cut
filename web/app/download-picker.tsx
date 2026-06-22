"use client";

import { useEffect, useState } from "react";

// Repo PÚBLICO (source-available) que hospeda código + releases. Links apontam pra
// release `latest`; nomes de asset são fixos (artifactName no electron-builder).
const RELEASE_REPO = "Edualnog/medusa-clip";
const releaseUrl = (asset: string) =>
  `https://github.com/${RELEASE_REPO}/releases/latest/download/${asset}`;

type Platform = "macOS" | "Windows" | "Linux";

const DOWNLOADS: {
  id: Platform;
  tab: string;
  variant: string;
  arch: string;
  format: string;
  asset: string;
  cmd: string;
}[] = [
  {
    id: "macOS",
    tab: "MACOS",
    variant: "APPLE SILICON",
    arch: "ARM64",
    format: ".DMG",
    asset: "MedusaClip-mac-arm64.dmg",
    cmd: `curl -L -o MedusaClip.dmg ${releaseUrl("MedusaClip-mac-arm64.dmg")} && open MedusaClip.dmg`,
  },
  {
    id: "Windows",
    tab: "WINDOWS",
    variant: "WINDOWS 10/11",
    arch: "X64",
    format: ".EXE",
    asset: "MedusaClip-win-x64.exe",
    cmd: `iwr ${releaseUrl("MedusaClip-win-x64.exe")} -OutFile MedusaClip.exe; .\\MedusaClip.exe`,
  },
  {
    id: "Linux",
    tab: "LINUX",
    variant: "LINUX DESKTOP",
    arch: "X64",
    format: ".APPIMAGE",
    asset: "MedusaClip-linux-x86_64.AppImage",
    cmd: `curl -L ${releaseUrl("MedusaClip-linux-x86_64.AppImage")} -o MedusaClip.AppImage && chmod +x MedusaClip.AppImage && ./MedusaClip.AppImage`,
  },
];

// Detecta o SO do visitante pra já abrir o card certo (fallback macOS).
function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "macOS";
  const s = `${navigator.platform} ${navigator.userAgent}`.toLowerCase();
  if (s.includes("win")) return "Windows";
  if (s.includes("linux") && !s.includes("android")) return "Linux";
  return "macOS";
}

export function DownloadPicker() {
  // Começa em macOS (igual no server) e ajusta pro SO real após montar — sem
  // mismatch de hidratação.
  const [active, setActive] = useState<Platform>("macOS");
  const [copied, setCopied] = useState(false);

  useEffect(() => setActive(detectPlatform()), []);

  const current = DOWNLOADS.find((d) => d.id === active) ?? DOWNLOADS[0];

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(current.cmd);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard bloqueado -> usuário seleciona manualmente */
    }
  }

  return (
    <div className="dl-picker">
      <div className="dl-tabs" role="tablist" aria-label="Escolha sua plataforma">
        {DOWNLOADS.map((d) => (
          <button
            key={d.id}
            type="button"
            role="tab"
            aria-selected={d.id === active}
            className={`dl-tab${d.id === active ? " is-active" : ""}`}
            onClick={() => setActive(d.id)}
          >
            <span>{d.tab}</span>
            <span>{d.format}</span>
          </button>
        ))}
      </div>

      <div className="dl-panel" role="tabpanel">
        <div className="dl-panel-head">
          <h3>{current.variant}</h3>
          <p>ARQUITETURA {current.arch}</p>
        </div>

        <a className="download-btn" href={releaseUrl(current.asset)} rel="noopener">
          BAIXAR {current.format}
        </a>

        <div className="dl-cmd">
          <span>OU NO TERMINAL</span>
          <div className="dl-cmd-box">
            <code>{current.cmd}</code>
            <button
              type="button"
              className="dl-copy"
              onClick={copyCommand}
              aria-label="Copiar comando"
            >
              {copied ? "COPIADO!" : "COPIAR"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
