# Registro P265 — verificação da configuração do broker

- Prompt P265 v1.1. Broker 0.43.0, entrada `7c7a989`. Mudanças locais
  anteriores preservadas e fora dos commits deste incremento.
- `--check-config` usa o carregamento de startup e os validadores
  TLS/política. Sucesso em JSON sem valores privados, código 2 em erro.
  README reconciliado com os aceites das fases 6–8 e fase 9 experimental.
- Windows/Rust 1.99.1: fmt e oito testes de configuração e versão PASS.
  O primeiro Clippy do binário identificou tamanho de `run`; a revisão
  extraiu bind e caminhos obrigatórios. Sem mudança de formato/estado.
- Suíte geral Windows: 246 testes da biblioteca passaram, um ignorado e
  um bloqueado por bind 10013. Ao separar esse teste, o binário admin
  legado ainda recusou três testes de CRUD Unix. Clippy estrito do
  pacote apontou imports e código Unix não usados no Windows.
- Gate completo Linux, interoperabilidade 2.1 e distribuição ainda
  dependem de execução na CI. WSL/Docker local bloqueados.
