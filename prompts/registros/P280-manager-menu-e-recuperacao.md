# P280 — menu e recuperação no Manager Windows

2026-11-08, America/Sao_Paulo. [Prompt P280](../broker/280-manager-menu-e-recuperacao.md).

- PASS: 21 testes, Clippy estrito e build release locked/offline do
  executável Windows. Recuperação seleciona somente falhas e respeita a
  ordem Broker, Admin, Client. A interface manteve ações e rótulos.
- BLOCKED: `sc.exe query` dos serviços Broker/Client e tentativa de
  iniciar Broker retornaram código 5. Diagnóstico do Manager instalado
  mostrou SCM indisponível. O binário novo recusou a operação em lote
  antes de qualquer alteração. A instalação ativa permanece pendente.
