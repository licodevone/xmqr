# Prompt — gate de conformidade QoS, sessões e retained

Execute depois de `25`–`29`. Este prompt é um **gate de evidência**, não autorização para chamar o broker de MQTT 3.1.1 completo. Use [OASIS MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html), `commands/mqtt-conformance.md`, `commands/mqtt-security-review.md` e a matriz normativa do projeto.

## Matriz mínima

| Área | Evidência indispensável |
|---|---|
| QoS 1 | PUBACK, retransmissão no reconnect, identifiers sem colisão, ACK só após ownership durável configurado |
| QoS 2 | PUBLISH/PUBREC/PUBREL/PUBCOMP, duplicação de cada etapa, encaminhamento idempotente, crash entre transições |
| Sessão | CleanSession 0/1, Session Present 0/1, replay offline/inflight, takeover, identidade vinculada, restart |
| Retained | substituição, deleção por payload vazio, RETAIN do replay vs fluxo normal, QoS mínimo, restart |
| Segurança/limites | ACL em publish/subscribe/replay, mTLS + senha, quotas e backpressure, buffer/CPU/disco sob carga |

1. Cada caso informa versão, pacote/feature, cláusula OASIS, pré-condições, estímulo, bytes ou resultado observável e ambiente. Inclua vetores wire independentes do encoder, testes unitários, integração, interoperabilidade com Mosquitto e outra biblioteca, fuzzing com limite e crash injetado antes/depois de commits/snapshots.
2. Execute `cargo fmt --check`, `cargo test --locked`, `cargo clippy --all-targets --locked -- -D warnings` e teste do MCP local. Se o lint falhar em débito preexistente, isole a falha; não marque o gate inteiro como aprovado.
3. Repita o ciclo com TLS/mTLS e ACL real em uma porta de teste distinta do broker do usuário. Valide PUBLISH/SUBSCRIBE com QoS 0/1/2, conexão longa, reboot do broker, cliente offline e retained. Não exponha credenciais em comandos, logs ou artefatos.
4. Atualize documentação do cliente e operador, ADRs, plano de migração/rollback e matriz de conformidade somente com evidências executadas. Relate funções não implementadas (Will, wildcard, MQTT 5 e outras), plataforma/`fsync` não verificados e limites de durabilidade, inclusive que crash de processo não prova segurança contra falta de energia.
