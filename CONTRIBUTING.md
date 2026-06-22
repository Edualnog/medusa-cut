# Contribuindo com o Medusa Clip

Obrigado pelo interesse! 💛 O Medusa Clip é **open source (AGPL-3.0)** e toda ajuda é bem-vinda.

Ao participar, você concorda em seguir nosso [Código de Conduta](CODE_OF_CONDUCT.md).

## Formas de ajudar

- 🐛 **Bugs:** abra uma [issue](https://github.com/Edualnog/medusa-clip/issues) com passos pra reproduzir, seu SO e a versão do app.
- 💡 **Ideias / features:** abra uma issue descrevendo o caso de uso.
- 🔧 **Código:** faça um fork, crie uma branch e abra um Pull Request.
- 📣 **Divulgação:** compartilhe com quem joga e cria conteúdo.
- 💸 **Apoio:** [medusaclip.com/apoiar](https://medusaclip.com/apoiar) (Pix ou cripto, sempre opcional).

## Rodando localmente

Veja a seção **Desenvolvimento** do [README](README.md):

```bash
cd agent   && make setup && make test   # motor de cortes (Python 3.11+)
cd desktop && npm install && npm start    # app Electron
cd web     && npm install && npm run dev  # landing
```

## Pull Requests

- Mantenha o PR focado em uma coisa só; descreva **o que** muda e **por quê**.
- Siga o estilo do código existente (Python: type hints; desktop: JS puro no `renderer/`).
- Rode os testes do motor (`cd agent && make test`) quando mexer nele.
- Princípios inegociáveis do projeto: **local-first**, **sem cadastro** e **BYO key** —
  nada de subir vídeo do usuário pra nuvem nem reintroduzir login/backend sem discussão.
- **Assine seus commits (DCO):** use `git commit -s`. Um CI verifica isso em todo PR.
  Detalhes em [DCO.md](DCO.md).

## Licença e DCO

Ao contribuir, você concorda que sua contribuição seja licenciada sob a **AGPL-3.0**,
a mesma do projeto.

Não usamos CLA. Em vez disso, cada commit deve ter um `Signed-off-by` (via `git commit
-s`), que certifica que você tem o direito de submeter aquele código sob a AGPL-3.0 —
o **Developer Certificate of Origin**. Veja [DCO.md](DCO.md).
