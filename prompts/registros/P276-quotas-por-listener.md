# Registro P276 — quota de conexões por listener

Data local: 2026-11-08, America/Sao_Paulo.
[Prompt P276 v1.0](../broker/276-quotas-por-listener.md).
Base `d128e47c04fa450b260d736555df69ea8c8aec71`.

- `[[listener_limits]]` aplica um teto opcional por endereço MQTT TCP,
  WS ou WSS, além do teto global. A admissão conta handshakes. As duas
  vagas são liberadas quando a tarefa de conexão termina.
- O preflight e o startup validam o teto contra o bind e o limite global
  efetivos. As métricas separam a recusa local (`listener_admission`) da
  global (`admission`). Nenhuma migração de estado é necessária.
- PASS: 250 testes de biblioteca (1 ignorado, 1 filtrado), 10 de
  configuração (2 ignorados) e 2 de versão. Cobertura local inclui
  configuração inválida, isolamento dos dois tetos e reuso de vaga.
- PASS: `cargo fmt --all -- --check` e Clippy local com exceções Windows
  preexistentes (`-A unused_imports -A dead_code`).
- BLOCKED: `saturated_tcp_listener_preserves_websocket_admission` foi
  executado explicitamente no Windows e parou na primeira conexão de
  loopback com WinError 10013, antes do MQTT CONNECT.

## Aceite pendente

Executar em Ubuntu na fonte exata:

```text
cargo test --locked --test configuration saturated_tcp_listener_preserves_websocket_admission -- --exact
```

A promoção depende da CI Ubuntu, do ensaio de capacidade integrado e
da verificação do pacote. Versão do manifesto permanece 0.45.0,
candidato experimental.

## Candidato e publicação

- Commit `fbea7e0c056a49ace4ba48f8fb398ff59037fe8f`.
- O push para `release/validation-p276` falhou por resolução DNS de
  `github.com`. Tag e release pendentes.
- Para acionar a CI em um terminal com acesso ao GitHub:

  ```powershell
  git push origin 'fbea7e0c056a49ace4ba48f8fb398ff59037fe8f:refs/heads/release/validation-p276'
  ```
