# P189 v1 — Packet Identifier zero em comandos MQTT 5

Estado de entrada: `main` limpo em `facb7124583b37d4a12967f720ad2862d34d2baa`, broker 0.33.0 e documento durável v15. P188 classificou identificador zero nos ACKs QoS. SUBSCRIBE, UNSUBSCRIBE e PUBLISH QoS 1/2 já rejeitam zero no codec, porém após CONNACK MQTT 5 a conexão fecha sem motivo explícito.

Objetivo observável: SUBSCRIBE, UNSUBSCRIBE e PUBLISH QoS 1/2 com Packet Identifier zero recebem DISCONNECT MQTT 5 `0x82` (Protocol Error) e fechamento, antes de qualquer alteração de assinatura, entrega, retained, transação QoS ou estado durável. PUBLISH QoS 0 não carrega Packet Identifier. MQTT 3.1.1 conserva o fechamento sem DISCONNECT MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §2.2.1, MQTT-2.2.1-2/3, exige ausência de identificador em QoS 0 e identificador não zero para novos SUBSCRIBE, UNSUBSCRIBE e PUBLISH QoS 1/2; §4.13.1 estabelece o fechamento por erro de protocolo e recomenda DISCONNECT `0x82` quando não houver motivo mais específico.

Escopo: `src/mqtt/codec.rs`, `src/mqtt/mod.rs`, verificador TCP próprio, `.github/workflows/ci.yml`, `docs/conformance/mqtt5-status.md`, plano e matriz, registro P189. Não alterar client independente, opções MQTT 5, versões, quotas, ACL, segurança, formato v15, ou a regra de P188 para ACKs.

Invariantes: classificação ocorre antes do roteador; Will segue a transição de erro; limite Maximum Packet Size é respeitado ao responder; nenhum ACK de sucesso confirma comando recusado; retomada durável e ACL permanecem corretas. Erro de escrita do DISCONNECT fecha a conexão. Truncamento e IDs não zero mantêm sua classificação anterior.

Compatibilidade: mudança apenas no wire de erro MQTT 5; MQTT 3.1.1 não recebe resposta MQTT 5. Sem migração e sem tag/release isolada. O broker publicado 0.33.0 não inclui este recorte até próximo marco validado.

Aceite: unidade para zero/não zero nas três famílias (PUBLISH QoS 1 e 2); TCP real para razões, Will, SUBSCRIBE sem criar assinatura, UNSUBSCRIBE sem remover assinatura, PUBLISH sem fanout/retained, reconexão durável e regressão MQTT 3.1.1. Gates `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings`, build release, licenças, distribuição, testes P188 e regressões afetadas. Registrar falhas intermediárias e CI do commit exato; fase 6A continua aberta.
