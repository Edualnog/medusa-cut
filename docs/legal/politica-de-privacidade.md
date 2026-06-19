# Política de Privacidade — Medusa Clip

> **Minuta — revisar com advogado.** Versão 2026-06-18.
> Fonte canônica. A cópia exibida no app vive em `desktop/renderer/legal.js` —
> manter as duas em sincronia.

Esta Política explica como o Medusa Clip trata dados pessoais, em conformidade com a Lei
Geral de Proteção de Dados (LGPD, Lei nº 13.709/2018).

## 1. Resumo
O Medusa Clip é **local-first**: seus vídeos e clipes ficam e são processados no seu
computador. **Nós não recebemos seus vídeos.** Não coletamos telemetria nem analytics.

## 2. Dados que ficam no seu dispositivo
- Sua chave da OpenRouter (**armazenada cifrada** pelo cofre do sistema operacional);
- Tokens da sua sessão de login (**cifrados**);
- Os clipes gerados, na pasta que você escolher;
- Estatísticas de custo/uso de IA e suas preferências do app.

## 3. Dados que saem do seu dispositivo
- **Login (Supabase):** seu e-mail e senha são enviados ao Supabase para autenticar sua
  conta.
- **Análise por IA (OpenRouter):** para gerar os cortes, o Aplicativo envia à OpenRouter
  — usando a *sua* chave — a transcrição do áudio, instruções (prompts) e **quadros
  (imagens) do seu vídeo**. Esse tratamento fica sujeito às políticas da OpenRouter e dos
  provedores de modelo.
- **Prévia de link (YouTube/Google):** ao colar um link, a URL é consultada no serviço
  oEmbed do YouTube para exibir título e miniatura.
- **Download por link:** ao baixar um vídeo público, o Aplicativo se conecta à plataforma
  de origem.

## 4. Finalidades e bases legais
Tratamos dados para autenticar sua conta e operar a assinatura (execução de contrato),
gerar os cortes solicitados (execução de contrato e seu consentimento ao usar o recurso)
e cumprir obrigações legais. O envio à OpenRouter ocorre por sua ação ao gerar clipes.

## 5. Compartilhamento (operadores)
Usamos provedores que atuam como operadores: **Supabase** (conta/autenticação) e, por
iniciativa sua, **OpenRouter** e provedores de modelos de IA (análise). A prévia usa
serviço do **Google/YouTube**. Não vendemos seus dados.

## 6. Transferência internacional
Alguns provedores podem processar dados fora do Brasil. Buscamos parceiros com
salvaguardas adequadas, conforme a LGPD.

## 7. Retenção
Dados de conta são mantidos enquanto a conta existir. Dados locais (chave, clipes,
preferências) permanecem no seu dispositivo até você removê-los ou desinstalar o
Aplicativo.

## 8. Seus direitos (LGPD)
Você pode solicitar confirmação de tratamento, acesso, correção, anonimização,
portabilidade, eliminação e informações sobre compartilhamento, além de revogar
consentimento. Para exercer, contate-nos (abaixo).

## 9. Segurança
Segredos sensíveis no dispositivo são cifrados pelo cofre do sistema operacional. Ainda
assim, nenhum sistema é 100% seguro; mantenha seu computador protegido.

## 10. Alterações
Esta Política pode ser atualizada; mudanças relevantes serão comunicadas no Aplicativo.

## 11. Contato e Encarregado (DPO)
Contato: privacidade@medusaclip.com. (Nome do Encarregado, razão social e CNPJ a
preencher.)
