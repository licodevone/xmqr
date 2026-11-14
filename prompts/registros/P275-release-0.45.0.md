# Registro P275 — candidato Broker 0.45.0

Data local: 2026-11-07, America/Sao_Paulo.
[Prompt P275 v1.0](../broker/275-release-0.45.0.md).
Base `ef5e5da058057db75d5c5a9607f6f25ea0012bac`.

- Manifestos e lockfiles principal e Windows Service, Dockerfile,
  changelog, notas e guia de reprodução atualizados. Sem alterações
  em fontes Rust, testes, dependências ou formato de estado.
- PASS: fmt, consistência da versão, 249 testes da biblioteca
  (1 ignorado, 1 filtrado), 9 de configuração (1 ignorado) e 2 de versão.
  O roteador manteve e recuperou 1.000 sessões.
- PASS: `mqtt-broker 0.45.0` e `mqtt-admin 0.45.0` em `--version`.
  Check locked/offline do Windows Service passou. Clippy local passou
  com exceções para avisos Windows preexistentes
  (`-A unused_imports -A dead_code`).
- BLOCKED: primeira conexão da fixture TCP retornou WinError 10013.
  WSL e Docker recusaram acesso. CI Ubuntu, admissão de 1.000
  clientes, ensaio integrado e verificação do pacote pendentes.

## Candidato e publicação

- Commit candidato `d128e47c04fa450b260d736555df69ea8c8aec71`.
- Push da branch de validação falhou por DNS. O SHA está ausente no
  GitHub. Gravação das notas via integração retornou HTTP 403.
- Tag `v0.45.0` e pré-release pendentes. Para acionar a CI a partir de
  terminal com acesso ao GitHub:

  ```powershell
  git -C 'D:\projects\my-project\acmebr-projects\xmqr.acmebr\xmqr' push origin 'd128e47c04fa450b260d736555df69ea8c8aec71:refs/heads/release/validation-0.45.0'
  ```

  Aplicar a tag após aceite da fonte exata, ensaio integrado e
  verificação do pacote.
