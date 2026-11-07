# Registro P269 — candidato 0.44.0

Data local: 2026-11-07. [Prompt P269 v1.1](../broker/269-release-0.44.0.md).
Base `4e7f1ecfedea35cfdf5e604a5d394ec7fbc5376e`.

## Preparação

- Broker e `mqtt-admin` legado na versão 0.44.0. Manifestos e lockfiles
  normal e de serviço Windows alinhados. Dockerfile usa 0.44.0 como padrão.
- Notas de release, changelog e P259 atualizados. O candidato tem o mesmo
  código Rust da base. As referências publicadas continuam na matriz.

## Evidência local

- PASS: verificação de formatação e consistência dos dois pares de manifesto
  e lockfile. O bump alterou apenas a versão do pacote local nesses arquivos.
- PASS: build debug offline com lockfile e `--version` dos dois binários.
  Saídas `mqtt-broker 0.44.0` e `mqtt-admin 0.44.0`.
- PASS: 8 testes de configuração e 2 de versão. Biblioteca: 248 passaram,
  1 ignorado e 1 filtrado (monitor TCP, dependente de socket local).
- PASS: `cargo check --locked --offline --manifest-path
  packaging/windows-service/Cargo.toml --bins`. Sem homologação de
  instalação e ciclo do serviço.
- FAIL: Clippy com `-D warnings` no Windows por imports e caminhos
  administrativos preexistentes sem uso nesse alvo.
- BLOCKED: inventário de licenças offline por falta de
  `linux-raw-sys 0.4.15` no cache. WSL e Docker Desktop recusaram acesso.

## Publicação

Git e GitHub CLI falharam na resolução DNS. A leitura por integração
confirmou que `v0.44.0` ainda não resolve no GitHub. O envio de conteúdo
pela mesma integração recebeu HTTP 403 no P268.

CI Ubuntu, integração TCP/WS, pacote e rollback do candidato pendentes.
Sem tag `v0.44.0`, pré-release ou anexos publicados.
