import Link from "next/link";
import { DownloadPicker } from "./download-picker";
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
  { number: "2", title: "CONECTE", text: "Entre na sua conta e conecte sua chave de IA — OpenRouter, OpenAI ou Anthropic." },
  { number: "3", title: "ESCOLHA", text: "Selecione um vídeo local ou cole um link público de gameplay." },
  { number: "4", title: "PUBLIQUE", text: "Receba clips 9:16 com título, legenda karaokê e reframe automático." },
];

const FAQ = [
  {
    question: "MEUS VÍDEOS SÃO ENVIADOS PARA ALGUM SERVIDOR?",
    answer: "Não. O processamento de vídeo e a biblioteca de clips ficam no seu computador. A sua conta usa o Supabase, mas seus gameplays não passam por ele.",
  },
  {
    question: "PRECISO DE INTERNET?",
    answer: "Para entrar na conta, falar com o provedor de IA e baixar vídeos por link, sim. Arquivos locais continuam sendo analisados e renderizados no seu PC.",
  },
  {
    question: "QUAIS PROVEDORES DE IA POSSO USAR?",
    answer: "OpenRouter, OpenAI ou Anthropic (Claude). Você escolhe o provedor no app e conecta a sua chave — se já tem créditos na OpenAI ou na Anthropic, é só usar. Dá pra trocar de provedor quando quiser.",
  },
  {
    question: "POR QUE USAR MINHA PRÓPRIA CHAVE DE IA?",
    answer: "Liberdade e transparência. A chave fica no seu dispositivo e fala direto com o provedor — você controla seu gasto e nada de IA passa pelos nossos servidores. É o que mantém o app gratuito.",
  },
  {
    question: "QUANTO CUSTA POR CORTE?",
    answer: "Centavos. Num teste com os modelos padrão, um vídeo de ~10 minutos gerou 4 cortes por poucos centavos de dólar no total — cerca de 1 centavo por corte. O valor varia com o provedor e o modelo que você escolhe e com o tamanho do vídeo, e é cobrado direto pelo provedor (OpenRouter, OpenAI ou Anthropic) na sua chave. O app não cobra nada.",
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
            <span className="beta-tag">BETA</span>
          </Link>

          <div className="nav-menu">
            <a href="#recursos">RECURSOS</a>
            <a href="#exemplos">EXEMPLOS</a>
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
            <div className="eyebrow">BETA · ESPECIALISTA EM GAMEPLAY · 100% LOCAL</div>
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
            <video
              poster="/hero-poster.jpg"
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              aria-label="Demonstração do Medusa Clip gerando clips de gameplay"
            >
              <source src="/hero.webm" type="video/webm" />
              <source src="/hero.mp4" type="video/mp4" />
            </video>
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

        <section className="section shell-width showcase-section" id="exemplos">
          <SectionTag>EXEMPLOS REAIS</SectionTag>
          <div className="section-heading">
            <h2>VEJA OS CORTES.<br />FEITOS PELO MOTOR.</h2>
            <p>
              Cortes 9:16 gerados pelo Medusa Clip: reframe automático, hook na abertura
              e legenda karaokê palavra a palavra. Ative o som pra ouvir.
            </p>
          </div>
          <div className="showcase-stage">
            <div className="phone-frame">
              <video
                poster="/cuts-poster.jpg"
                autoPlay
                muted
                loop
                playsInline
                controls
                preload="metadata"
                aria-label="Exemplos de cortes verticais gerados pelo Medusa Clip"
              >
                <source src="/cuts.webm" type="video/webm" />
                <source src="/cuts.mp4" type="video/mp4" />
              </video>
            </div>
          </div>
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

          <DownloadPicker />
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
              O Medusa Clip é gratuito. A IA roda na SUA chave — OpenRouter, OpenAI ou
              Anthropic — você paga só o custo real dos modelos, direto ao provedor, e o
              resto é seu: seus clips ficam no seu PC, suas chaves no seu controle, sua
              liberdade intacta.
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
              O app é grátis. O único custo é a IA — e é da SUA chave (OpenRouter, OpenAI
              ou Anthropic), cobrada direto pelo provedor, em centavos por corte. Sem
              assinatura, sem créditos, sem intermediário. Você escolhe o provedor e o
              modelo: mais barato custa ainda menos.
            </p>
          </div>
          <div className="price-card">
            <span className="price-label">CUSTO REAL · SUA CHAVE</span>
            <div className="price">
              ~US$ 0,01 <span>/ CORTE</span>
            </div>
            <ul>
              <li>EXEMPLO: VÍDEO DE ~10 MIN → 4 CORTES POR POUCOS CENTAVOS (MODELOS PADRÃO)</li>
              <li>OPENROUTER, OPENAI OU ANTHROPIC — VOCÊ ESCOLHE; OPÇÕES MAIS BARATAS CUSTAM MENOS</li>
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

        <p>© 2026 MEDUSA CLIP. TODOS OS DIREITOS RESERVADOS.</p>

        <div className="footer-social">
          <a
            href="https://discord.gg/dB79XXBz"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Discord do Medusa Clip"
            title="Discord"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
              <path d="M20.32 4.37A19.8 19.8 0 0 0 15.45 3a13.7 13.7 0 0 0-.62 1.27 18.27 18.27 0 0 0-5.66 0A13.5 13.5 0 0 0 8.54 3a19.74 19.74 0 0 0-4.88 1.37C.56 9 .04 13.47.3 17.89a19.92 19.92 0 0 0 6.04 3.06c.49-.66.92-1.36 1.29-2.1-.71-.27-1.39-.59-2.04-.98.17-.13.34-.26.5-.4a14.23 14.23 0 0 0 12.16 0c.16.14.33.27.5.4-.65.39-1.34.71-2.05.98.37.74.8 1.44 1.29 2.1a19.9 19.9 0 0 0 6.05-3.06c.31-5.12-.53-9.55-3.5-13.52ZM8.02 15.2c-1.16 0-2.12-1.07-2.12-2.38 0-1.31.94-2.38 2.12-2.38 1.19 0 2.14 1.08 2.12 2.38 0 1.31-.94 2.38-2.12 2.38Zm7.96 0c-1.17 0-2.12-1.07-2.12-2.38 0-1.31.94-2.38 2.12-2.38 1.19 0 2.14 1.08 2.12 2.38 0 1.31-.93 2.38-2.12 2.38Z" />
            </svg>
          </a>
          <a
            href="https://github.com/Edualnog/medusa-cut"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub do Medusa Clip"
            title="GitHub"
          >
            <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
            </svg>
          </a>
          <Link href="/login" className="footer-login">ENTRAR</Link>
        </div>
      </footer>
    </>
  );
}
