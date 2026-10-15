# P107 — fronteira de leitura do canal administrativo

- Prompt: [P107 rev1–2](../broker/107-canal-admin-implementacao.md).
- Entrega parcial: Unix socket opt-in Linux/WSL, UID do peer, tokens viewer e
  operator distintos/privados, status JSON v1, quotas e deadline, readiness
  pelo ator. [Contrato provisório](../../docs/admin-channel.md).
- Nenhuma mutação online, recibo durável ou auditoria neste incremento.
  `reload` por canal é recusado; A09/A05/A07 e fase 5 permanecem abertos.
- Gates: `cargo fmt --check`, 116 testes unitários PASS/6 ignorados e suíte de
  integração existente PASS; Clippy `-D warnings`; build debug do broker;
  inventário de licenças atualizado/aceito. Teste de processo real
  `verify_admin_channel.py` passou status viewer/operator, token ruim,
  operação mutante recusada, request grande, rejeição de política estática,
  remoção do socket no shutdown e ausência dos tokens/caminho privado no log.
  Tudo em diretório temporário Linux/WSL, sem instância do operador.
