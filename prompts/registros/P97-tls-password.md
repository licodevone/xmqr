# P97 — TLS com senha e ACL sem certificado cliente

- Entrada: `beabcbb2ff3aa4e0cf471400e708280c0621722c`, tag `v0.12.0`,
  árvore limpa; prompt [P97](../broker/97-tls-password.md) criado antes do código.
- Implementação: modo `tls-password` opt-in, TLS 1.2/1.3 com certificado do
  servidor, autenticação MQTT usuário/senha e ACL exata deny-by-default;
  `client_ca`/`client_crl` recusados e estado separado por perfil. mTLS padrão
  preservado; adicionais B09 continuam exclusivos de `secure-mtls`.
- Integração Ubuntu 26.04/WSL: `scripts/verify_tls_password.py` PASS com client
  C48 em QoS0/1/2, negativas de senha, usuário, CA, SAN e ACL; configuração
  client CA/CRL e identidade do client recusadas. Credenciais/certificados
  gerados em diretório temporário, sem log de senha.
- Regressão: `scripts/verify_multi_endpoint.py` PASS com os binários novos:
  endpoints mTLS, QoS0/1/2 cruzado, limite agregado, retained/restart e
  negativos CA/credenciais.
- Gates antes do bump: `cargo test --locked -- --test-threads=1`, `cargo fmt
  --all -- --check`, `cargo clippy --locked --all-targets -- -D warnings` e
  `cargo build --locked --bins` PASS. Gate final da versão no registro de
  publicação, se houver.
- Limites: B09 políticas por endpoint, B11 rotação e E02 físico não são cobertos
  por P97; não constitui prontidão de produção nem reload geral do TOML.
