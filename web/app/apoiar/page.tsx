"use client";

import { useState } from "react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { MedusaLogo } from "../medusa-logo";

// --- Pix (chave aleatória) ---
const PIX_KEY = "145df37e-2226-4027-8ad0-fd4d1b811c56";
const PIX_NAME = "ERISSON EDUARDO NOGUEIRA"; // máx. 25 chars (campo 59 do BR Code)
const PIX_CITY = "PORTO ALEGRE"; // máx. 15 chars (campo 60)
const PIX_RECEIVER = "Erisson Eduardo Nogueira · Banco XP";

// --- Cripto (endereços públicos de recebimento) ---
const CRYPTO: { name: string; network: string; address: string }[] = [
  {
    name: "POL · USDC · USDT",
    network: "Polygon",
    address: "0xd87CdFE4323701fA47aA94966e085bBcC42a7332",
  },
];

// Monta o "Pix Copia e Cola" (BR Code / EMV) sem valor — o doador escolhe quanto.
function emv(id: string, value: string) {
  return `${id}${value.length.toString().padStart(2, "0")}${value}`;
}
function crc16(payload: string) {
  let crc = 0xffff;
  for (let i = 0; i < payload.length; i++) {
    crc ^= payload.charCodeAt(i) << 8;
    for (let j = 0; j < 8; j++) {
      crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
      crc &= 0xffff;
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, "0");
}
function buildPixPayload() {
  const merchantAccount = emv("00", "br.gov.bcb.pix") + emv("01", PIX_KEY);
  const payload =
    emv("00", "01") +
    emv("26", merchantAccount) +
    emv("52", "0000") +
    emv("53", "986") +
    emv("58", "BR") +
    emv("59", PIX_NAME) +
    emv("60", PIX_CITY) +
    emv("62", emv("05", "***")) +
    "6304";
  return payload + crc16(payload);
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="copy-btn"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1800);
        } catch {
          /* ignore */
        }
      }}
    >
      {done ? "✓ COPIADO!" : label}
    </button>
  );
}

export default function ApoiarPage() {
  const pixPayload = buildPixPayload();

  return (
    <>
      <header className="site-header">
        <nav className="nav shell-width" aria-label="Navegação">
          <Link href="/" className="brand" aria-label="Medusa Clip — início">
            <MedusaLogo size={34} />
            <span>MEDUSA CLIP</span>
            <span className="beta-tag">BETA</span>
          </Link>
          <div className="nav-menu">
            <Link href="/">INÍCIO</Link>
            <Link href="/#download">DOWNLOAD</Link>
            <a href="https://github.com/Edualnog/medusa-clip" target="_blank" rel="noopener noreferrer">
              GITHUB
            </a>
          </div>
          <Link href="/#download" className="nav-login">
            BAIXAR
          </Link>
        </nav>
      </header>

      <main>
        <section className="donate-page">
          <div className="donate-intro">
            <div className="eyebrow">APOIE O PROJETO · OPEN SOURCE</div>
            <h1>
              APOIE O <span>MEDUSA CLIP</span>
            </h1>
            <p className="hero-text">
              Grátis e open source (AGPL-3.0), no espírito do Blender. Doe por{" "}
              <strong>Pix</strong> ou <strong>cripto</strong>, quanto quiser — sem
              intermediário e sem taxa. Valeu! 💛
            </p>
            <p className="hero-note">DOAÇÃO OPCIONAL · NUNCA UM PAYWALL · O APP SEGUE GRÁTIS</p>
          </div>

          <div className="donate-card">
            {/* PIX */}
            <div className="donate-method">
              <h3 className="donate-method-title">DOAR VIA PIX</h3>
              <p className="donate-method-sub">{PIX_RECEIVER}</p>

              <div className="donate-qr">
                <QRCodeSVG value={pixPayload} size={172} level="M" marginSize={2} />
              </div>

              <div className="copy-field">
                <span className="donate-label">PIX COPIA E COLA</span>
                <code className="copy-code">{pixPayload}</code>
                <CopyButton text={pixPayload} label="COPIAR CÓDIGO PIX" />
              </div>

              <div className="copy-field">
                <span className="donate-label">CHAVE PIX (ALEATÓRIA)</span>
                <code className="copy-code">{PIX_KEY}</code>
                <CopyButton text={PIX_KEY} label="COPIAR CHAVE" />
              </div>

              <p className="donate-foot">
                Abra seu banco → Pix → ler QR Code (ou colar o código) → escolha o valor.
                Sem taxa, cai na hora.
              </p>
            </div>

            {/* CRIPTO */}
            <div className="donate-method">
              <h3 className="donate-method-title">DOAR COM CRIPTO</h3>
              {CRYPTO.map((c) => (
                <div className="crypto-item" key={c.network + c.address}>
                  <span className="donate-label">
                    REDE {c.network.toUpperCase()} · {c.name}
                  </span>
                  <div className="donate-qr">
                    <QRCodeSVG value={c.address} size={148} level="M" marginSize={2} />
                  </div>
                  <code className="copy-code">{c.address}</code>
                  <CopyButton text={c.address} label="COPIAR ENDEREÇO" />
                </div>
              ))}
              <p className="donate-foot">
                ⚠️ Envie <strong>somente na rede Polygon</strong>. Token enviado em outra
                rede pode se perder.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer shell-width">
        <div className="footer-brand">
          <Link href="/" className="brand">
            <MedusaLogo size={28} />
            <span>MEDUSA CLIP</span>
            <span className="beta-tag">BETA</span>
          </Link>
          <a className="footer-support" href="mailto:suporte@medusaclip.com">
            SUPORTE@MEDUSACLIP.COM
          </a>
        </div>
        <p>© 2026 MEDUSA CLIP · OPEN SOURCE (AGPL-3.0) · SEM CADASTRO</p>
        <div className="footer-social">
          <Link href="/#download" className="footer-login">BAIXAR</Link>
        </div>
      </footer>
    </>
  );
}
