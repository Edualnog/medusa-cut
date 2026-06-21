// Notas de atualizacao do Medusa Clip.
// O topo da lista e a versao MAIS RECENTE. `version` deve casar com package.json.
// O app abre estas notas automaticamente no 1o boot apos atualizar (ver app.js).
window.CHANGELOG = [
  {
    version: "0.1.20",
    date: "2026-06-21",
    title: "Notas de atualizacao, suporte e convidar amigos",
    items: [
      "Notas de atualizacao: abrem no 1o boot apos atualizar e tambem clicando na versao no rodape.",
      "Suporte & comunidade na aba Conta: e-mail de suporte, Discord e GitHub.",
      "Convidar amigos: compartilhe o app em 1 clique (copiar link, Discord, WhatsApp, X, e-mail).",
    ],
  },
  {
    version: "0.1.19",
    date: "2026-06-21",
    title: "Hook queimado, score viral e player interno",
    items: [
      "Hook (manchete) queimado nos primeiros ~5s do clipe, na divisa abaixo da facecam.",
      "Score de viralizacao colorido por faixa em cada card da biblioteca.",
      "Player do clipe DENTRO do app (modal) + preview no hover do card.",
      "Biblioteca com ordenacao (mais recentes, mais antigos, maior score).",
    ],
  },
  {
    version: "0.1.17",
    date: "2026-06-21",
    title: "Muito mais rapido (~25min -> ~3-5min)",
    items: [
      "Analise viral e render dos cortes rodando em PARALELO.",
      "Legenda karaoke fundida no proprio render (1 encode em vez de 2).",
      "Download em h264 <=1080p pra evitar AV1 1440p (era o maior gargalo).",
      "Transcricao na GPU: MLX no Mac (Apple Silicon) e CUDA no Windows, com fallback seguro pra CPU.",
    ],
  },
  {
    version: "0.1.14",
    date: "2026-06-20",
    title: "Layout simplificado e mais certeiro",
    items: [
      "Dois layouts: facecam no terco superior + blur, ou foco na acao em tela cheia.",
      "Deteccao de facecam so nos cantos superiores (ignora rosto de NPC no meio da tela).",
    ],
  },
  {
    version: "0.1.10",
    date: "2026-06-19",
    title: "Multi-provedor e seguranca",
    items: [
      "Conecte sua propria chave: OpenRouter, OpenAI ou Anthropic (Claude).",
      "Chave de IA e sessao de login cifradas no disco.",
      "Onboarding de primeiro acesso com aceites e escolha da pasta dos clips.",
    ],
  },
];
