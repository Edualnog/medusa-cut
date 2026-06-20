import Image from "next/image";
import Link from "next/link";
import { MedusaLogo } from "./medusa-logo";

const BENEFITS = [
  {
    number: "01",
    title: "SEU VÍDEO NÃO SOBE",
    text: "O gameplay entra e sai no seu computador. Nada de esperar upload ou entregar arquivos brutos para uma nuvem.",
  },
  {
    number: "02",
    title: "USA A FORÇA DO SEU PC",
    text: "Transcrição, análise de movimento, enquadramento e render usam o hardware que você já tem.",
  },
  {
    number: "03",
    title: "FEITO PARA GAMEPLAY",
    text: "A seleção combina áudio, movimento e visão para encontrar ação, reação, clutch, fail e payoff visual.",
  },
];

const STEPS = [
  { number: "1", title: "INSTALE", text: "Baixe a versão certa para o seu sistema e abra o Medusa Clip." },
  { number: "2", title: "CONECTE", text: "Entre na sua conta e conecte sua própria chave da OpenRouter." },
  { number: "3", title: "ESCOLHA", text: "Selecione um vídeo local ou cole um link público de gameplay." },
  { number: "4", title: "PUBLIQUE", text: "Receba clips 9:16 com título, legenda karaokê e reframe automático." },
];

// Repo PÚBLICO que hospeda só os instaladores (o código-fonte é privado). Os links
// apontam pra release `latest`, e os nomes de asset são fixos (artifactName no
// electron-builder do desktop).
const RELEASE_REPO = "Edualnog/medusa-clip-releases";
const releaseUrl = (asset: string) =>
  `https://github.com/${RELEASE_REPO}/releases/latest/download/${asset}`;
const RELEASES_READY = !RELEASE_REPO.includes("PLACEHOLDER");

const DOWNLOADS = [
  { platform: "macOS", variant: "APPLE SILICON", architecture: "ARM64", format: ".DMG", asset: "MedusaClip-mac-arm64.dmg" },
  { platform: "macOS", variant: "INTEL", architecture: "X64", format: ".DMG", asset: "MedusaClip-mac-x64.dmg" },
  { platform: "Windows", variant: "WINDOWS 10/11", architecture: "X64", format: ".EXE", asset: "MedusaClip-win-x64.exe" },
  { platform: "Linux", variant: "LINUX DESKTOP", architecture: "X64", format: ".APPIMAGE", asset: "MedusaClip-linux-x64.AppImage" },
];

const FAQ = [
  {
    question: "MEUS VÍDEOS SÃO ENVIADOS PARA ALGUM SERVIDOR?",
    answer: "Não. O processamento de vídeo e a biblioteca de clips ficam no seu computador. A sua conta usa o Supabase, mas seus gameplays não passam por ele.",
  },
  {
    question: "PRECISO DE INTERNET?",
    answer: "Para entrar na conta, usar a OpenRouter e baixar vídeos por link, sim. Arquivos locais continuam sendo analisados e renderizados no seu PC.",
  },
  {
    question: "POR QUE USAR MINHA PRÓPRIA CHAVE DA OPENROUTER?",
    answer: "Porque você paga o custo real dos modelos, direto ao provedor, sem comprar pacotes de créditos inflados da Medusa Clip.",
  },
  {
    question: "FUNCIONA COM QUALQUER JOGO?",
    answer: "A análise principal é genérica para gameplay: áudio, movimento, fala e frames. Isso permite trabalhar com FPS, simuladores, survival, corrida e outros gêneros.",
  },
  {
    question: "QUANDO OS INSTALADORES SERÃO LIBERADOS?",
    answer: "Os builds estão sendo preparados e testados por plataforma. A página mostrará o download assim que cada versão estiver assinada e pronta.",
  },
];

function SectionTag({ children }: { children: React.ReactNode }) {
  return <div className="section-tag">{children}</div>;
}

export default function Home() {
  return (
    <>
      <header className="site-header">
        <nav className="nav shell-width" aria-label="Navegação principal">
          <Link href="/" className="brand" aria-label="Medusa Clip — início">
            <MedusaLogo size={34} />
            <span>MEDUSA CLIP</span>
          </Link>

          <div className="nav-menu">
            <a href="#recursos">RECURSOS</a>
            <a href="#download">DOWNLOAD</a>
            <a href="#preco">PREÇO</a>
          </div>

          <Link href="/login" className="nav-login">
            ENTRAR
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero shell-width">
          <div className="hero-copy">
            <div className="eyebrow">PROCESSAMENTO 100% LOCAL</div>
            <h1>
              SEU GAMEPLAY.
              <br />
              SEU PC.
              <br />
              <span>SEUS MELHORES CLIPS.</span>
            </h1>
            <p className="hero-text">
              Transforme vídeos longos em clips verticais com IA, legenda karaokê e
              enquadramento automático — sem enviar seu gameplay para uma nuvem.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#download">
                VER DOWNLOADS
              </a>
              <a className="button button-secondary" href="#como-funciona">
                COMO FUNCIONA
              </a>
            </div>
            <p className="hero-note">MACOS · WINDOWS · LINUX · SUA CHAVE OPENROUTER</p>
          </div>

          <figure className="app-preview">
            <div className="window-bar">
              <span>MEDUSA-CLIP.APP</span>
              <span>LOCAL</span>
            </div>
            <Image
              src="/desktop-app-preview.png"
              alt="Aplicativo Medusa Clip aberto na tela de geração local"
              width={1280}
              height={633}
              priority
              sizes="(max-width: 900px) 100vw, 48vw"
            />
            <figcaption>
              O VÍDEO ENTRA, É PROCESSADO E FICA NO SEU COMPUTADOR.
            </figcaption>
          </figure>
        </section>

        <div className="proof-strip" aria-label="Diferenciais principais">
          <div className="shell-width proof-strip-inner">
            <span>SEM UPLOAD</span>
            <span>FFMPEG INCLUSO</span>
            <span>IA MULTIMODAL</span>
            <span>CLIPS 9:16</span>
          </div>
        </div>

        <section className="section shell-width" id="recursos">
          <SectionTag>POR QUE RODAR LOCAL</SectionTag>
          <div className="section-heading">
            <h2>MAIS RÁPIDO PARA VOCÊ.<br />MAIS PRIVADO POR PADRÃO.</h2>
            <p>
              Sem fila de VPS e sem upload de arquivos gigantes. Você começa mais
              rápido e mantém o controle sobre o material bruto.
            </p>
          </div>
          <div className="benefit-grid">
            {BENEFITS.map((benefit) => (
              <article className="benefit-card" key={benefit.number}>
                <span className="card-number">{benefit.number}</span>
                <h3>{benefit.title}</h3>
                <p>{benefit.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section section-bordered shell-width" id="como-funciona">
          <SectionTag>DO VÍDEO AO CLIP</SectionTag>
          <div className="section-heading compact">
            <h2>QUATRO PASSOS.<br />NENHUM UPLOAD.</h2>
          </div>
          <ol className="step-grid">
            {STEPS.map((step) => (
              <li key={step.number}>
                <span className="step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="section shell-width download-section" id="download">
          <SectionTag>ESCOLHA SUA VERSÃO</SectionTag>
          <div className="section-heading">
            <h2>MEDUSA CLIP<br />NO SEU SISTEMA.</h2>
            <p>
              Cada build inclui o aplicativo, o motor de cortes, FFmpeg e FFprobe.
              Sem instalar Python ou configurar dependências.
            </p>
          </div>

          <div className="download-grid">
            {DOWNLOADS.map((download) => (
              <article className="download-card" key={`${download.platform}-${download.variant}`}>
                <div className="download-card-top">
                  <span>{download.platform}</span>
                  <span>{download.format}</span>
                </div>
                <h3>{download.variant}</h3>
                <p>ARQUITETURA {download.architecture}</p>
                {RELEASES_READY ? (
                  <a className="download-btn" href={releaseUrl(download.asset)} rel="noopener">
                    BAIXAR
                  </a>
                ) : (
                  <button type="button" disabled>
                    EM BREVE
                  </button>
                )}
              </article>
            ))}
          </div>
          <p className="download-note">
            OS INSTALADORES SERÃO LIBERADOS AQUI APÓS ASSINATURA E TESTES EM CADA PLATAFORMA.
          </p>
        </section>

        <section className="section shell-width pricing-section" id="preco">
          <div className="pricing-copy">
            <SectionTag>PREÇO</SectionTag>
            <h2>GRÁTIS.<br />SEM PEGADINHA.</h2>
            <p>
              O Medusa Clip é gratuito. Você só paga os modelos de IA direto na sua
              própria chave da OpenRouter — sem mensalidade, sem créditos, sem margem nossa.
            </p>
          </div>
          <article className="price-card">
            <span className="price-label">MEDUSA CLIP</span>
            <div className="price">GRÁTIS <span>/ SEMPRE</span></div>
            <ul>
              <li>Processamento local de gameplay</li>
              <li>Análise viral multimodal</li>
              <li>Legenda karaokê e reframe automático</li>
              <li>Atualizações para desktop</li>
            </ul>
            <Link className="button button-primary" href="/login">
              CRIAR CONTA
            </Link>
          </article>
        </section>

        <section className="section shell-width faq-section">
          <SectionTag>PERGUNTAS FREQUENTES</SectionTag>
          <div className="faq-list">
            {FAQ.map((item) => (
              <details key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="final-cta">
          <div className="shell-width final-cta-inner">
            <div>
              <span>MEDUSA CLIP PARA DESKTOP</span>
              <h2>SEU PRÓXIMO CLIP<br />COMEÇA NO SEU PC.</h2>
            </div>
            <a className="button button-dark" href="#download">
              VER VERSÕES
            </a>
          </div>
        </section>
      </main>

      <footer className="footer shell-width">
        <Link href="/" className="brand">
          <MedusaLogo size={28} />
          <span>MEDUSA CLIP</span>
        </Link>
        <p>© 2026 MEDUSA CLIP. TODOS OS DIREITOS RESERVADOS.</p>
        <Link href="/login">ENTRAR</Link>
      </footer>
    </>
  );
}
