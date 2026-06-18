// Landing 8-bit do Zorothax. Estatica por enquanto — auth + app vem nas
// proximas fases. O design segue a referencia pixel/gamer.
import { Fragment } from "react";
import Link from "next/link";
import { MedusaLogo } from "./medusa-logo";

const STEPS = [
  { icon: "gamepad", title: "1. COLE O LINK", text: "Cole o link do seu vídeo de gameplay" },
  { icon: "ai", title: "2. IA ANALISA", text: "Nossa IA encontra as melhores jogadas e momentos do vídeo" },
  { icon: "swords", title: "3. CORTES ÉPICOS", text: "Criamos clips de jogadas épicas, wins, fails e momentos engraçados" },
  { icon: "trophy", title: "4. BAIXE E COMPARTILHE", text: "Baixe, edite como quiser e publique para sua comunidade" },
];

const DEMO_CLIPS = [
  { hook: "TRIPLE KILL!", tc: "00:01 - 00:15" },
  { hook: "VICTORY!", tc: "00:15 - 00:32" },
  { hook: "PENTA KILL!", tc: "00:32 - 00:48" },
  { hook: "WTF?!", tc: "00:48 - 01:02" },
  { hook: "EPIC WIN!", tc: "01:02 - 01:18" },
];

const FEATURES = [
  {
    icon: "🎮",
    title: "FEITO PRA GAMES",
    text: "Genéricos tipo OpusClip cortam por transcrição e não entendem gameplay. A Zorothax acha o momento por FUSÃO DE SINAIS (áudio + cena): kill, clutch, fail, reação.",
  },
  {
    icon: "👁",
    title: "A IA VÊ A TELA",
    text: "Nosso juiz é MULTIMODAL: olha os frames do corte, não só a legenda. Acerta o que é realmente épico — gameplay é visual.",
  },
  {
    icon: "⚡",
    title: "MUITO MAIS BARATO",
    text: "Você usa SUA própria chave de IA e paga centavos por vídeo, direto. Sem créditos inflados. A assinatura é só da ferramenta.",
  },
];

const USAGE = [
  { n: "1", title: "CRIE SUA CONTA", text: "Cadastro rápido, sem cartão pra testar." },
  { n: "2", title: "CONECTE SUA CHAVE", text: "Cole sua chave da OpenRouter (fica segura, criptografada). Você paga só o uso real da IA." },
  { n: "3", title: "COLE O LINK E GERE", text: "A Zorothax processa na nuvem e te entrega os melhores cortes, prontos pro TikTok." },
];

const FAQ = [
  {
    q: "É melhor que o OpusClip pra games?",
    a: "Sim. Eles são genéricos; a Zorothax é focada em gameplay — acha kill/clutch/fail por sinais de áudio e cena, e a IA vê a tela.",
  },
  {
    q: "Preciso instalar algo?",
    a: "Não — roda 100% na nuvem, direto no navegador. Você só conecta sua chave e cola o link.",
  },
  {
    q: "Por que usar minha própria chave?",
    a: "Você paga o custo real da IA (centavos por vídeo), sem créditos inflados. Mais transparente e muito mais barato que os concorrentes.",
  },
  {
    q: "Funciona com qualquer jogo?",
    a: "Sim. Áudio + cena funcionam pra qualquer gameplay, de FPS a simulador.",
  },
];

function Icon({ name }: { name: string }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 2 } as const;
  switch (name) {
    case "gamepad":
      return (
        <svg width="48" height="48" viewBox="0 0 24 24" {...p}>
          <rect x="2" y="7" width="20" height="10" />
          <path d="M6 10v4M4 12h4M15 11h.01M18 13h.01" />
        </svg>
      );
    case "ai":
      return (
        <svg width="48" height="48" viewBox="0 0 24 24" {...p}>
          <rect x="3" y="8" width="18" height="9" />
          <path d="M8 4l1 3M16 4l-1 3M12 11l1 2-2 0 1 2" />
        </svg>
      );
    case "swords":
      return (
        <svg width="48" height="48" viewBox="0 0 24 24" {...p}>
          <path d="M4 4l9 9M20 4l-9 9M3 17l4 4M21 17l-4 4M9 15l-3 3M15 15l3 3" />
        </svg>
      );
    case "trophy":
      return (
        <svg width="48" height="48" viewBox="0 0 24 24" {...p}>
          <path d="M7 4h10v5a5 5 0 0 1-10 0V4zM7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3M10 16v3M14 16v3M8 21h8" />
        </svg>
      );
    default:
      return null;
  }
}

export default function Home() {
  return (
    <>
      <nav className="nav">
        <span className="brand">
          <MedusaLogo size={30} /> ZOROTHAX
        </span>
        <Link href="/login" className="nav-link">ENTRAR</Link>
      </nav>
      <main className="wrap">
      {/* badge */}
      <div className="row-center">
        <div className="badge">✦ NOVO: IA AINDA MAIS PRECISA ✦</div>
      </div>

      {/* hero */}
      <h1 className="hero">
        Transforme vídeos de games
        <br />
        em <span className="ghost">clips</span> perfeitos
      </h1>
      <p className="sub">
        Para criadores e canais de games. Corte os melhores momentos, jogadas
        épicas, wins, fails e momentos engraçados dos seus vídeos de gameplay.
      </p>

      {/* cta */}
      <div className="cta">
        <label className="input">
          <span aria-hidden>🔗</span>
          <input placeholder="Cole o link do seu vídeo de gameplay aqui..." />
        </label>
        <Link className="btn" href="/app">
          GERAR CLIPS →
        </Link>
      </div>
      <p className="supports">
        Suporta <b>▶ YouTube</b> · <b>♪ TikTok</b> · e muito mais
      </p>

      {/* como funciona */}
      <div className="section-tag" id="como-funciona">
        <div className="badge">COMO FUNCIONA</div>
      </div>
      <div className="steps">
        {STEPS.map((s, i) => (
          <Fragment key={s.title}>
            <div className="step">
              <div className="icon">
                <Icon name={s.icon} />
              </div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </div>
            {i < STEPS.length - 1 && <div className="arrow pixel">→</div>}
          </Fragment>
        ))}
      </div>

      {/* funciona com */}
      <div className="works">
        <span>▸ FUNCIONA COM:</span>
        <span className="item">▶ YOUTUBE</span>
        <span className="item">♪ TIKTOK</span>
        <span className="item">◎ INSTAGRAM</span>
        <span className="item">f FACEBOOK</span>
        <span>⋯ E MAIS...</span>
      </div>

      {/* janela clips gerados */}
      <div className="window">
        <div className="titlebar">
          <div className="dots">
            <span />
            <span />
            <span />
          </div>
          <div className="label">↧ ✕</div>
        </div>
        <div className="window-body">
          <div>
            <div className="preview">
              <div className="play" />
            </div>
            <div className="timecode">00:00 / 45:21</div>
          </div>
          <div>
            <div className="clips-title">CLIPS GERADOS</div>
            <div className="cards">
              {DEMO_CLIPS.map((c) => (
                <div className="card" key={c.hook}>
                  <div className="thumb">
                    <div className="hook">{c.hook}</div>
                  </div>
                  <div className="tc">{c.tc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* por que medusa (foco gamer vs opusclip) */}
      <div className="section-tag">
        <div className="badge">POR QUE ZOROTHAX</div>
      </div>
      <div className="features">
        {FEATURES.map((f) => (
          <div className="feature box" key={f.title}>
            <div className="feature-icon" aria-hidden>{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.text}</p>
          </div>
        ))}
      </div>

      {/* como o usuario usa (BYO key + agente) */}
      <div className="section-tag">
        <div className="badge">COMO VOCÊ USA</div>
      </div>
      <div className="usage">
        {USAGE.map((u) => (
          <div className="usage-step box" key={u.n}>
            <div className="usage-n">{u.n}</div>
            <h3>{u.title}</h3>
            <p>{u.text}</p>
          </div>
        ))}
      </div>

      {/* preco */}
      <div className="section-tag">
        <div className="badge">PREÇO · 1 PLANO, SEM CRÉDITOS</div>
      </div>
      <div className="row-center">
        <div className="box price-card">
          <div className="plan-name">ZOROTHAX PRO</div>
          <div className="plan-price">
            R$11,90<span>/mês</span>
          </div>
          <ul className="dash-list">
            <li>✓ Clips ilimitados (você usa sua própria chave de IA)</li>
            <li>✓ Sem créditos — custo de IA real, direto na OpenRouter</li>
            <li>✓ Análise viral multimodal + legenda karaokê + reframe automático</li>
            <li>✓ Processamento no seu PC (rápido e privado)</li>
          </ul>
          <Link href="/login" className="btn full">
            COMEÇAR AGORA →
          </Link>
        </div>
      </div>

      {/* faq */}
      <div className="section-tag">
        <div className="badge">FAQ</div>
      </div>
      <div className="faq">
        {FAQ.map((f) => (
          <div className="faq-item box" key={f.q}>
            <h4>{f.q}</h4>
            <p>{f.a}</p>
          </div>
        ))}
      </div>

      <p className="foot">Zorothax · clips de games nível Opus Clip</p>
      </main>
    </>
  );
}
