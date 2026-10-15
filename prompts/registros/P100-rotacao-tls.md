# P100 — rotação TLS transacional

- Prompt [P100](../broker/100-rotacao-tls.md) criado antes da alteração; base
  `v0.13.1`/`1e72082f5163ecba58b0ffa8aaf231df80ed41c3`.
- SIGUSR1 Unix relê cert/key/CA/CRL em tarefa bloqueante e publica uma geração
  para novos handshakes; falha conserva a anterior. Endpoints mTLS compartilham
  essa geração; TLS-senha recarrega somente cert/key. Sessões existentes não são
  desconectadas e SIGHUP mantém seu contrato de bundle.
- Validação temporal de servidor/CA/CRL, assinatura e emissor CRL, par de chave
  e configuração rustls antes de swap. CRL vencida ou de outra CA é recusada.
- Ubuntu26/WSL: `verify_tls_rotation.py` PASS em chave inválida, CRL divergente,
  servidor vencido/PEM malformado, CA vencida, CRL vencida/assinatura inválida,
  rotação/rollback, revogação e
  sessão ativa nos dois endpoints. `verify_tls_password.py` PASS em rotação e
  rollback com client sem certificado; P96 regressão PASS.
- `cargo fmt --all -- --check`, `cargo test --locked` (114 testes da lib, 6
  campanhas explícitas ignoradas, demais binários/integrações PASS), `cargo
  clippy --locked --all-targets -- -D warnings`, `cargo build --locked --bins`
  PASS antes de P101. Inventário de 136 dependências PASS; coletor de 261
  avisos PASS após suplemento do `asn1-rs-impl` na revisão upstream exata.
- Limites: não recarrega TOML, não encerra conexões anteriores, não é teste
  físico E02 nem comprovação de produção. Ver
  [contrato operacional](../../docs/security/secure-transport.md).
