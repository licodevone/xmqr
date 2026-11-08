# Registro P273 — candidato 0.44.0 com quota de 500

Data local: 2026-11-07, America/Sao_Paulo.
[Prompt P273 v1.0](../broker/273-release-044-capacidade.md).
Base `02097af27efe601ada936dc964d82936e6771e5a`.

- Candidato incorpora os limites P271, o roteiro P270 e o ensaio P272.
  Changelog, notas e instruções de rollback atualizados.
- PASS: fmt, 249 testes de biblioteca, 9 de configuração e 2 de versão
  no Windows. Biblioteca com 1 ignorado e 1 filtrado, integração de
  configuração com 1 ignorado. O teste do ator com 500 sessões passou.
- PASS: Clippy com `-D warnings -A unused_imports -A dead_code` para
  código administrativo dependente de Unix no alvo Windows. Python:
  7 testes da fixture de pressão e `--help` do ensaio integrado.
- BLOCKED: WSL, Docker e acesso TCP loopback. CI Ubuntu, execução
  integrada, ciclo do pacote e checksums pendentes.
- A versão `0.44.0` e a tag proposta continuam reservadas ao Broker
  e ao `mqtt-admin` legado. A validação e distribuição dos componentes
  independentes têm ciclos próprios.
