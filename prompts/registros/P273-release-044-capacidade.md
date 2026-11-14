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

## Fonte e tentativa de publicação

- Commit candidato: `389c4897aeaef143f60a4ff496d320e7e45c2913`. Inclui P270–P273.
- Push para `release/validation-0.44.0` falhou por DNS. A consulta
  GitHub confirmou que o SHA ainda estava ausente. Tentativa de gravar
  o objeto das notas recebeu HTTP 403 da integração.
- Tag e release pendentes. Enviar o commit exato de um terminal
  autorizado para acionar a CI. Validar pacote e executar a integração
  antes de aplicar a tag.

  ```sh
  git push origin '389c4897aeaef143f60a4ff496d320e7e45c2913:refs/heads/release/validation-0.44.0'
  ```
