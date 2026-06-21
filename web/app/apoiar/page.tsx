"use client";

import { useState } from "react";
import Link from "next/link";
import { MedusaLogo } from "../medusa-logo";

// Coletivo no Open Collective. O dono precisa criar o coletivo com ESTE slug
// (ou trocar aqui pelo slug real). Enquanto não existir, o botão Doar leva a um 404.
const OPEN_COLLECTIVE_SLUG = "medusa-clip";
const CURRENCY_SYMBOL = "$";
const PRESETS = [5, 10, 25, 50, 100, 250];

type Interval = "month" | "oneTime";

function donateUrl(amount: number, interval: Interval) {
  const base = `https://opencollective.com/${OPEN_COLLECTIVE_SLUG}/donate`;
  const params = new URLSearchParams({ amount: String(amount) });
  if (interval === "month") params.set("interval", "month");
  return `${base}?${params.toString()}`;
}

export default function ApoiarPage() {
  const [interval, setInterval] = useState<Interval>("month");
  const [selected, setSelected] = useState<number>(10);
  const [custom, setCustom] = useState<string>("");

  const customValue = Number(custom);
  const amount = custom.trim() && customValue > 0 ? customValue : selected;
  const valid = amount > 0;

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
            <a href="https://github.com/Edualnog/medusa-cut" target="_blank" rel="noopener noreferrer">
              GITHUB
            </a>
          </div>
          <Link href="/#download" className="nav-login">
            BAIXAR
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero donate-hero shell-width">
          <div className="hero-copy">
            <div className="eyebrow">APOIE O PROJETO · OPEN SOURCE</div>
            <h1>
              AJUDE O MEDUSA CLIP
              <br />
              <span>A CRESCER.</span>
            </h1>
            <p className="hero-text">
              O Medusa Clip é <strong>grátis e open source (AGPL-3.0)</strong>: sem
              anúncios, sem paywall, sem vender seus dados. Se ele te economiza tempo,
              considere apoiar — é o que mantém o desenvolvimento de pé.
            </p>
            <p className="hero-text">
              No espírito do Blender: <strong>feito pela comunidade, pra comunidade</strong>.
              Se cada usuário ativo doasse alguns dólares por mês, o projeto estaria
              garantido o ano inteiro. Toda doação conta. Valeu!
            </p>
            <p className="hero-note">DOAÇÃO OPCIONAL · NUNCA UM PAYWALL · O APP SEGUE GRÁTIS</p>
          </div>

          <div className="donate-card">
            <div className="donate-toggle" role="tablist" aria-label="Frequência da doação">
              <button
                type="button"
                role="tab"
                aria-selected={interval === "month"}
                className={interval === "month" ? "active" : ""}
                onClick={() => setInterval("month")}
              >
                MENSAL
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={interval === "oneTime"}
                className={interval === "oneTime" ? "active" : ""}
                onClick={() => setInterval("oneTime")}
              >
                ÚNICA
              </button>
            </div>

            <div className="donate-amounts">
              {PRESETS.map((value) => (
                <button
                  type="button"
                  key={value}
                  className={!custom.trim() && selected === value ? "donate-amount selected" : "donate-amount"}
                  onClick={() => {
                    setSelected(value);
                    setCustom("");
                  }}
                >
                  {CURRENCY_SYMBOL} {value}
                </button>
              ))}
            </div>

            <p className="donate-sub">
              {interval === "month" ? "Doar todo mês" : "Doar uma vez"}
            </p>

            <div className="donate-custom">
              <span className="donate-symbol">{CURRENCY_SYMBOL}</span>
              <input
                type="number"
                min={1}
                inputMode="decimal"
                placeholder="Outro valor"
                aria-label="Valor personalizado"
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
              />
            </div>

            <a
              className={valid ? "button button-primary donate-submit" : "button button-primary donate-submit disabled"}
              href={valid ? donateUrl(amount, interval) : undefined}
              target="_blank"
              rel="noopener noreferrer"
              aria-disabled={!valid}
            >
              DOAR {CURRENCY_SYMBOL} {valid ? amount : "—"} {interval === "month" ? "/ MÊS" : ""} →
            </a>

            <p className="donate-foot">
              Pagamento seguro via <strong>Open Collective</strong> — transparência total:
              você vê pra onde vai cada centavo.
            </p>
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
