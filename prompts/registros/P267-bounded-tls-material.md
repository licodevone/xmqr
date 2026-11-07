# Registro P267 — leitura limitada de material TLS

- Prompt P267 v1.1. Entrada `d561321`, Broker 0.43.0, branch
  `codex/p265-p266-xmqr-operacao`. Escopo isolado em transporte, testes
  e guia TLS. As fases e a aceitação anterior mantêm seu estado registrado.
- O módulo PEM limita a leitura de cadeias, chave e CAs a 1 MiB por
  arquivo, e de CRLs a 8 MiB. A leitura recusa alvos não regulares e
  valida tamanho do handle e bytes lidos. A validação de validade das
  CAs produz os certificados decodificados usados para verificar as CRLs.
- Windows, Rust 1.99.1, Cargo locked/offline. Fmt PASS. Suíte da biblioteca
  com exclusão explícita de `endpoints_detect_actor_stop_and_monitor_teardown`
  por bind 10013 conhecido: 248 PASS, 1 ignorado e 1 filtrado. Configuração
  e versão: 9 PASS. Após a correção v1.1, repetição de PEM e configuração
  com 2 e 7 PASS, respectivamente.
- Teste funcional isolado com `--check-config` e certificados/CRLs
  sintéticos do runtime .NET: 4 PASS. Duas CAs e duas CRLs válidas,
  assinatura alterada na segunda CRL, CRL acima de 8 MiB e chave acima
  de 1 MiB com prefixo válido. Nenhum estado criado. OpenSSL do Git
  retornou 3221225794 ao iniciar e foi substituído nesse teste.
- Clippy estrito detectou avisos preexistentes no Windows e lint na
  conversão de erro PEM. O P267 v1.1 corrigiu os avisos introduzidos. A
  repetição sem promoção dos avisos passou, com avisos anteriores em
  auth/router e na asserção preexistente do teste P265.
- Linux/WSL, teste de link simbólico Unix, rotação por SIGUSR1,
  interoperabilidade e pacote ainda precisam dos gates próprios. Sem
  medição de throughput MQTT. Tag de versão e release dependem do aceite
  completo, inclusive o P265 da base.
