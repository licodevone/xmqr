# P279 — fechamento do Broker 0.45.0

2026-11-08, America/Sao_Paulo. [Prompt P279](../broker/279-finalizar-0.45.0.md).
Base `fbea7e0`, com P277/P278 incorporados à fonte de validação.

- PASS: 252 testes de biblioteca, 11 de configuração e 2 de versão
  no Windows. A suíte portátil filtrou um teste dependente de loopback
  e manteve os ignores de integração da plataforma.
- A CI do pacote agora verifica instalação a partir do `.deb` 0.43.0
  por SHA-256, versão 0.45.0, recuperação com o binário instalado e
  retorno à 0.43.0. A campanha usa estado descartável.
- BLOCKED: WSL e Docker Desktop recusaram acesso. Gates Unix, pacote
  e publicação precisam da branch de validação no GitHub.
