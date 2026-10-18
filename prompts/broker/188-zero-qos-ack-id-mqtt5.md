# P188 v1 — Packet Identifier zero em ACKs QoS MQTT 5

Estado de entrada: `main` limpo em `f5a3a8f24c5b71f21663c6888bee1aec0d2d7d83`, broker 0.33.0, estado durável v15. P187 classifica propriedades inválidas em PUBACK/PUBREC/PUBREL/PUBCOMP. O codec já rejeita Packet Identifier zero, mas a conexão MQTT 5 apenas fecha sem motivo explícito.

Objetivo observável: após CONNACK MQTT 5, receber qualquer dos quatro ACKs QoS com Packet Identifier zero causa DISCONNECT `0x82` (Protocol Error), seguido de fechamento, sem processar o ACK nem liberar obrigação QoS durável. MQTT 3.1.1 continua fechando sem pacote MQTT 5. O Will aplicável segue a transição de desconexão por erro.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §2.2.1 (MQTT-2.2.1-3/5) exige identificador não zero para o PUBLISH original e o mesmo identificador no ACK; §4.13.1 define fechamento e DISCONNECT `0x82` para Protocol Error, quando não houver motivo mais específico.

Escopo: `src/mqtt/codec.rs`, `src/mqtt/mod.rs`, teste TCP em `scripts/`, documentação de conformidade, checklist e registro P188. Não alterar cliente independente, outros tipos de pacote, motivos de ACK válidos, segurança, quotas, formato persistido, versões nem perfil padrão.

Invariantes: classificar antes de mutar roteador/sessão; preservar QoS 1/2, geração, ACL, Will, limite Maximum Packet Size da resposta e commit durável. Erro de transporte ao enviar DISCONNECT ainda encerra a conexão. Identificador não zero não muda de comportamento.

Compatibilidade e migração: somente resposta wire de erro em MQTT 5; MQTT 3.1.1 permanece como antes. Sem migração v15; broker/client/admin publicados seguem com versões independentes. Release/tag somente em marco validado, não nesta fatia isolada.

Aceite: unidade cobre os quatro ACKs e IDs zero/não zero; TCP real cobre os quatro DISCONNECTs, Will, obrigação QoS 1 durável preservada e regressão MQTT 3.1.1. Rodar `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings`, build release, inventário de licenças e integração P188/regressões pertinentes. Registrar PASS/FAIL/BLOCKED com comandos e limites reais; não marcar fase 6A concluída.
