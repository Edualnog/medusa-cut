// Textos legais (minutas PT-BR) carregados como script para respeitar a CSP do
// renderer (default-src 'self' — sem fetch/iframe de arquivo local).
// FONTE CANONICA: docs/legal/*.md — manter em sincronia ao editar.
// AVISO: minutas para MVP. Revisar com advogado antes de produção.
window.LEGAL = {
  version: "2026-06-19",

  terms: `
    <p class="legal-draft">Minuta — revisar com advogado. Versão 2026-06-19.</p>
    <h2>Termos de Uso — Medusa Clip</h2>
    <p>Ao instalar, acessar ou usar o aplicativo Medusa Clip ("Aplicativo"), você
    concorda com estes Termos de Uso. Se não concordar, não use o Aplicativo.</p>

    <h3>1. O que é o Medusa Clip</h3>
    <p>O Medusa Clip é um aplicativo de desktop que transforma vídeos de gameplay em
    cortes verticais usando inteligência artificial. <strong>O processamento de vídeo
    acontece no seu computador</strong>; seus vídeos e clipes não são enviados para
    nossos servidores.</p>

    <h3>2. Elegibilidade</h3>
    <p>Você declara ter <strong>18 anos ou mais</strong> e capacidade civil para
    aceitar estes Termos.</p>

    <h3>3. Conta</h3>
    <p>O login usa autenticação por e-mail e senha. Você é responsável por manter suas
    credenciais em segurança e por toda atividade na sua conta.</p>

    <h3>4. Chave da OpenRouter (modelo "traga sua chave")</h3>
    <p>A análise por IA usa <strong>a sua própria chave da OpenRouter</strong>. O custo
    dos modelos é cobrado diretamente pela OpenRouter na sua conta — o Medusa Clip não
    intermedeia nem adiciona margem sobre esse consumo. Você é responsável pela guarda e
    pelo uso da sua chave e pelos custos gerados.</p>

    <h3>5. Preço</h3>
    <p>O Aplicativo é <strong>gratuito</strong>. Não há assinatura, mensalidade nem
    créditos. Você arca apenas com o custo dos modelos de IA, cobrado diretamente pela
    OpenRouter na sua chave (cláusula 4).</p>

    <h3>6. Responsabilidade pelo conteúdo e direitos autorais</h3>
    <p>Você é o único responsável pelos vídeos que processa. Ao usar o Aplicativo, você
    declara que <strong>possui os direitos necessários</strong> sobre o conteúdo (autoria,
    licença ou autorização) e que o uso não viola direitos de terceiros nem leis
    aplicáveis. Ao baixar vídeos por link, você deve respeitar os termos de uso da
    plataforma de origem (por exemplo, os Termos do YouTube). O Medusa Clip não concede
    qualquer direito sobre conteúdos de terceiros.</p>

    <h3>7. Uso aceitável</h3>
    <p>Você concorda em não usar o Aplicativo para fins ilícitos, para processar conteúdo
    sem direitos, para contornar proteções técnicas de terceiros, ou para qualquer
    finalidade que viole estes Termos ou a lei.</p>

    <h3>8. Propriedade intelectual</h3>
    <p>O Aplicativo, sua marca e seu código são de titularidade do Medusa Clip e/ou de
    seus licenciadores. Os clipes que você gera a partir do seu próprio conteúdo são
    seus.</p>

    <h3>9. Isenção de garantias</h3>
    <p>O Aplicativo é fornecido "no estado em que se encontra", sem garantias de
    resultado, disponibilidade ininterrupta ou adequação a um fim específico. A
    qualidade dos cortes depende de fatores como o conteúdo de origem e os modelos de IA
    de terceiros.</p>

    <h3>10. Limitação de responsabilidade</h3>
    <p>Na máxima extensão permitida pela lei, o Medusa Clip não se responsabiliza por
    danos indiretos, lucros cessantes, perda de dados, custos de IA gerados pela sua
    chave, ou por uso indevido de conteúdo de terceiros por você.</p>

    <h3>11. Suspensão e rescisão</h3>
    <p>Podemos suspender ou encerrar o acesso em caso de violação destes Termos. Você
    pode parar de usar o Aplicativo a qualquer momento.</p>

    <h3>12. Alterações</h3>
    <p>Estes Termos podem ser atualizados. Mudanças relevantes serão comunicadas no
    Aplicativo, podendo ser solicitado novo aceite.</p>

    <h3>13. Lei aplicável e foro</h3>
    <p>Estes Termos são regidos pelas leis da República Federativa do Brasil. Fica eleito
    o foro do domicílio do consumidor para dirimir controvérsias.</p>

    <h3>14. Contato</h3>
    <p>Dúvidas: contato@medusaclip.com. (Razão social, CNPJ e endereço a preencher.)</p>
  `,

  privacy: `
    <p class="legal-draft">Minuta — revisar com advogado. Versão 2026-06-19.</p>
    <h2>Política de Privacidade — Medusa Clip</h2>
    <p>Esta Política explica como o Medusa Clip trata dados pessoais, em conformidade com
    a Lei Geral de Proteção de Dados (LGPD, Lei nº 13.709/2018).</p>

    <h3>1. Resumo</h3>
    <p>O Medusa Clip é <strong>local-first</strong>: seus vídeos e clipes ficam e são
    processados no seu computador. <strong>Nós não recebemos seus vídeos.</strong> Não
    coletamos telemetria nem analytics de uso.</p>

    <h3>2. Dados que ficam no seu dispositivo</h3>
    <ul>
      <li>Sua chave da OpenRouter (<strong>armazenada cifrada</strong> pelo cofre do
      sistema operacional);</li>
      <li>Tokens da sua sessão de login (<strong>cifrados</strong>);</li>
      <li>Os clipes gerados, na pasta que você escolher;</li>
      <li>Estatísticas de custo/uso de IA e suas preferências do app.</li>
    </ul>

    <h3>3. Dados que saem do seu dispositivo</h3>
    <ul>
      <li><strong>Login (Supabase):</strong> seu e-mail e senha são enviados ao Supabase
      para autenticar sua conta.</li>
      <li><strong>Aceites legais (Supabase):</strong> registramos a versão dos Termos e
      desta Política que você aceitou, com data e hora, vinculados à sua conta — como
      prova de consentimento.</li>
      <li><strong>Análise por IA (OpenRouter):</strong> para gerar os cortes, o
      Aplicativo envia à OpenRouter — usando a <em>sua</em> chave — a transcrição do
      áudio, instruções (prompts) e <strong>quadros (imagens) do seu vídeo</strong>. Esse
      tratamento fica sujeito às políticas da OpenRouter e dos provedores de modelo.</li>
      <li><strong>Prévia de link (YouTube/Google):</strong> ao colar um link, a URL é
      consultada no serviço oEmbed do YouTube para exibir título e miniatura.</li>
      <li><strong>Download por link:</strong> ao baixar um vídeo público, o Aplicativo se
      conecta à plataforma de origem.</li>
    </ul>

    <h3>4. Finalidades e bases legais</h3>
    <p>Tratamos dados para autenticar sua conta (execução de contrato), gerar os cortes
    solicitados (execução de contrato e seu consentimento ao usar o recurso) e cumprir
    obrigações legais. O envio à OpenRouter ocorre por sua
    ação ao gerar clipes.</p>

    <h3>5. Compartilhamento (operadores)</h3>
    <p>Usamos provedores que atuam como operadores: <strong>Supabase</strong> (conta/
    autenticação) e, por iniciativa sua, <strong>OpenRouter</strong> e provedores de
    modelos de IA (análise). A consulta de prévia usa serviço do <strong>Google/
    YouTube</strong>. Não vendemos seus dados.</p>

    <h3>6. Transferência internacional</h3>
    <p>Alguns provedores podem processar dados fora do Brasil. Buscamos parceiros que
    adotem salvaguardas adequadas, conforme a LGPD.</p>

    <h3>7. Retenção</h3>
    <p>Dados de conta são mantidos enquanto a conta existir. Dados locais (chave, clipes,
    preferências) permanecem no seu dispositivo até você removê-los ou desinstalar o
    Aplicativo.</p>

    <h3>8. Seus direitos (LGPD)</h3>
    <p>Você pode solicitar confirmação de tratamento, acesso, correção, anonimização,
    portabilidade, eliminação e informações sobre compartilhamento, além de revogar
    consentimento. Para exercer, contate-nos (abaixo).</p>

    <h3>9. Segurança</h3>
    <p>Segredos sensíveis no dispositivo são cifrados pelo cofre do sistema operacional.
    Ainda assim, nenhum sistema é 100% seguro; mantenha seu computador protegido.</p>

    <h3>10. Alterações</h3>
    <p>Esta Política pode ser atualizada; mudanças relevantes serão comunicadas no
    Aplicativo.</p>

    <h3>11. Contato e Encarregado (DPO)</h3>
    <p>Contato: privacidade@medusaclip.com. (Nome do Encarregado, razão social e CNPJ a
    preencher.)</p>
  `,
};
