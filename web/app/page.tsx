import Image from "next/image";
import Link from "next/link";
import { MedusaLogo } from "./medusa-logo";

const BENEFITS = [
  {
    number: "01",
    title: "ESPECIALISTA EM GAMEPLAY",
    text: "O motor foi feito do zero e afinado só pra gameplay: combina áudio, movimento e visão pra achar clutch, fail, clímax e reação — com a precisão que recortador genérico não tem.",
  },
  {
    number: "02",
    title: "GRÁTIS, COM A SUA CHAVE",
    text: "O app é 100% gratuito. A IA roda na SUA própria chave — você paga só o custo real dos modelos, direto ao provedor, sem intermediário e sem trava.",
  },
  {
    number: "03",
    title: "SEU GAMEPLAY, SUA LIBERDADE",
    text: "Tudo processa no seu PC e a biblioteca fica no seu disco. Seu gameplay nunca sobe pra nuvem. Seus vídeos, suas chaves, seu controle.",
  },
];

const STEPS = [
  { number: "1", title: "INSTALE", text: "Baixe a versão certa para o seu sistema e abra o Medusa Clip." },
  { number: "2", title: "CONECTE", text: "Entre na sua conta e conecte sua própria chave da OpenRouter." },
  { number: "3", title: "ESCOLHA", text: "Selecione um vídeo local ou cole um link público de gameplay." },
  { number: "4", title: "PUBLIQUE", text: "Receba clips 9:16 com título, legenda karaokê e reframe automático." },
];

// Repo PÚBLICO (source-available) que hospeda código + releases. Os links apontam
// pra release `latest`, e os nomes de asset são fixos (artifactName no
// electron-builder do desktop).
const RELEASE_REPO = "Edualnog/medusa-cut";
const releaseUrl = (asset: string) =>
  `https://github.com/${RELEASE_REPO}/releases/latest/download/${asset}`;
const RELEASES_READY = !RELEASE_REPO.includes("PLACEHOLDER");

const DOWNLOADS = [
  { platform: "macOS", variant: "APPLE SILICON", architecture: "ARM64", format: ".DMG", asset: "MedusaClip-mac-arm64.dmg" },
  { platform: "Windows", variant: "WINDOWS 10/11", architecture: "X64", format: ".EXE", asset: "MedusaClip-win-x64.exe" },
  { platform: "Linux", variant: "LINUX DESKTOP", architecture: "X64", format: ".APPIMAGE", asset: "MedusaClip-linux-x86_64.AppImage" },
];

// Comando de 1 linha pra baixar pelo terminal de cada SO (alternativa ao botão).
function downloadCommand(platform: string, asset: string) {
  const url = releaseUrl(asset);
  switch (platform) {
    case "macOS":
      return `curl -L -o MedusaClip.dmg ${url} && open MedusaClip.dmg`;
    case "Windows": // PowerShell
      return `iwr ${url} -OutFile MedusaClip.exe; .\\MedusaClip.exe`;
    case "Linux":
      return `curl -L ${url} -o MedusaClip.AppImage && chmod +x MedusaClip.AppImage && ./MedusaClip.AppImage`;
    default:
      return "";
  }
}

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
    question: "POR QUE USAR MINHA PRÓPRIA CHAVE DE IA?",
    answer: "Liberdade e transparência. A chave fica no seu dispositivo e fala direto com o provedor — você controla seu gasto e nada de IA passa pelos nossos servidores. É o que mantém o app gratuito.",
  },
  {
    question: "QUANTO CUSTA POR CORTE?",
    answer: "Centavos. Num teste com os modelos padrão (GPT-4.1), um vídeo de ~10 minutos gerou 4 cortes por poucos centavos de dólar no total — cerca de 1 centavo por corte. O valor varia com o modelo que você escolhe e com o tamanho do vídeo, e é cobrado direto pela OpenRouter na sua chave. O app não cobra nada.",
  },
  {
    question: "O QUE TORNA OS CORTES MELHORES QUE UM RECORTADOR GENÉRICO?",
    answer: "O Medusa Clip é especializado em gameplay. Em vez de tratar tudo como vídeo de fala, ele lê áudio, movimento e os frames pra reconhecer o que importa num gameplay: clutch, fail, clímax, reação e a ação na tela — incluindo momentos de pura jogada, sem comentário.",
  },
  {
    question: "FUNCIONA COM QUALQUER JOGO?",
    answer: "Sim. A especialização é em gameplay, não em um título só — funciona com FPS, battle royale, survival, corrida, MOBA e mais, detectando ação, facecam e os melhores momentos.",
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
            <a href="#custo">CUSTO</a>
            <a href="#liberdade">GRÁTIS</a>
          </div>

          <Link href="/login" className="nav-login">
            ENTRAR
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero shell-width">
          <div className="hero-copy">
            <div className="eyebrow">ESPECIALISTA EM GAMEPLAY · 100% LOCAL</div>
            <h1>
              FEITO PRA
              <br />
              GAMEPLAY.
              <br />
              <span>SEUS MELHORES CLIPS.</span>
            </h1>
            <p className="hero-text">
              Recortadores genéricos tratam gameplay como vídeo qualquer. O Medusa Clip é
              especializado em gameplay: acha o clutch, o fail e o clímax que os outros
              erram. Gratuito, com a SUA chave de IA e rodando no SEU PC — seu gameplay
              nunca sobe pra nuvem.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#download">
                BAIXAR GRÁTIS
              </a>
              <a className="button button-secondary" href="#como-funciona">
                COMO FUNCIONA
              </a>
            </div>
            <p className="hero-note">GRÁTIS · MACOS · WINDOWS · LINUX · SUA CHAVE DE IA</p>
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
            <span>ESPECIALISTA EM GAMEPLAY</span>
            <span>100% GRÁTIS</span>
            <span>SUA CHAVE DE IA</span>
            <span>SEM UPLOAD</span>
          </div>
        </div>

        <section className="section shell-width" id="recursos">
          <SectionTag>POR QUE MEDUSA CLIP</SectionTag>
          <div className="section-heading">
            <h2>FEITO PRA GAMEPLAY.<br />DO SEU JEITO, NO SEU PC.</h2>
            <p>
              Ferramentas genéricas tratam gameplay como vídeo qualquer e perdem o
              melhor momento. O Medusa Clip é especializado — e te deixa no controle:
              de graça, com a sua chave de IA, sem nada subindo pra nuvem.
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
                  <>
                    <div className="download-cmd">
                      <span>OU NO TERMINAL</span>
                      <code>{downloadCommand(download.platform, download.asset)}</code>
                    </div>
                    <a className="download-btn" href={releaseUrl(download.asset)} rel="noopener">
                      BAIXAR
                    </a>
                  </>
                ) : (
                  <button type="button" disabled>
                    EM BREVE
                  </button>
                )}
              </article>
            ))}
          </div>
          <p className="download-note">
            CADA INSTALADOR JÁ TRAZ O APP, O MOTOR DE CORTES, FFMPEG E FFPROBE EMBUTIDOS — E É GRÁTIS. SEM PYTHON, SEM DEPENDÊNCIAS.
            <br />
            PRIMEIRA ABERTURA: NO MACOS, CLIQUE COM O BOTÃO DIREITO NO APP → ABRIR. NO WINDOWS, EM &quot;MAIS INFORMAÇÕES&quot; → EXECUTAR ASSIM MESMO.
          </p>
        </section>

        <section className="section section-bordered shell-width" id="liberdade">
          <SectionTag>GRÁTIS E NO SEU CONTROLE</SectionTag>
          <div className="section-heading">
            <h2>GRÁTIS DE VERDADE.<br />SEM TRAVA.</h2>
            <p>
              O Medusa Clip é gratuito. A IA roda na SUA chave da OpenRouter — você paga
              só o custo real dos modelos, direto ao provedor, e o resto é seu: seus
              clips ficam no seu PC, suas chaves no seu controle, sua liberdade intacta.
            </p>
          </div>
          <div className="hero-actions">
            <Link className="button button-primary" href="/login">
              CRIAR CONTA GRÁTIS
            </Link>
            <a className="button button-secondary" href="#download">
              BAIXAR AGORA
            </a>
          </div>
        </section>

        <section className="section shell-width pricing-section" id="custo">
          <div className="pricing-copy">
            <SectionTag>CUSTO TRANSPARENTE</SectionTag>
            <h2>CENTAVOS POR CORTE.<br />SEM SURPRESA.</h2>
            <p>
              O app é grátis. O único custo é a IA — e é da SUA chave da OpenRouter,
              cobrada direto pelo provedor, em centavos por corte. Sem assinatura, sem
              créditos, sem intermediário. Você escolhe o modelo: mais barato custa ainda
              menos.
            </p>
          </div>
          <div className="price-card">
            <span className="price-label">CUSTO REAL · SUA CHAVE</span>
            <div className="price">
              ~US$ 0,01 <span>/ CORTE</span>
            </div>
            <ul>
              <li>EXEMPLO: VÍDEO DE ~10 MIN → 4 CORTES POR POUCOS CENTAVOS (MODELOS PADRÃO GPT-4.1)</li>
              <li>VOCÊ ESCOLHE O MODELO NA OPENROUTER — OPÇÕES MAIS BARATAS CUSTAM MENOS</li>
              <li>SEM ASSINATURA E SEM CRÉDITOS: PAGA DIRETO AO PROVEDOR</li>
              <li>O APP É 100% GRÁTIS — O CUSTO DA IA É SEU E TRANSPARENTE</li>
            </ul>
            <a className="button button-primary" href="#download">
              BAIXAR GRÁTIS
            </a>
          </div>
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
