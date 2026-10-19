# Fase 8 / T02 — bridge entre brokers

Checkpoint em19/10/2026: **fase8/T02 ACEITA no contrato experimental P235**,
com client0.43.0/bridge0.5.0 publicados e conferidos. Este documento confronta o
[contrato P235](../prompts/broker/235-fase8-contrato-integrado.md), sob
[prompt P237](../prompts/broker/237-aceite-fase8-distribuicao.md).

O sidecar independente `mqtt-bridge` pertence ao pacote do client. Broker,
client e admin mantêm versões próprias. A interface web/admin e os indicadores
ON-LINE/OFF-LINE têm aceite A23–A25 separado e não substituem a bridge.

## Requisitos e evidências

| P235 | Implementação e prova | Estado |
| --- | --- | --- |
| 1. Mapeamentos limitados e isolamento | C147/C148: configv2,1–8rotas, identidades/estado por rota, `--check` sem rede/escrita, sobreposição/topologia/quota recusadas; regressão23/23 | PASS local e CI exata |
| 2. MQTT5/propriedades/TTL | `bridge_metadata.rs` e `bridge_v5.rs`: PFI, ContentType, ResponseTopic com política explícita, CorrelationData e UserProperties ordenadas/repetidas; prazo absoluto recalculado após commit; alias/subID removidos na transformação | Wire33PASS/1NOT_RUN e unitários; debug/pacote/imagem PASS no recorte |
| 3. QoS/retained | Seis combinações de QoS por direção, retained inicial/vivo/tombstone, origem menor que assinatura | Matriz real34/34PASS debug/pacote/imagem |
| 4. Estado/recuperação | Journalformato2 privado/checksum/lock/limite/identidade; fases Prepared/Sent/Rel/Done/Refused; checkpoints e retomada por perna, recusa de corrupção/sessão ausente | Recuperação16/16PASS debug local/CI; parada/retomada também em ELFs release |
| 5. Percurso | `xmqr.bridge.path` limitado, retorno/teto descartados duravelmente; manifesto acíclico preservado, cadeia3brokers e encaminhador cooperante; teste finito da remoção do marcador | Local PASS; fronteira não cooperante explícita |
| 6. Segurança/limites | CA/SAN/senha/certificado inválidos em cada perna, ACLsourceSUBACK/destPUBLISH, burstQoS0 com obrigação preservada; SIGTERM normal e retomada sem ACK prematuro; retries/quotas, disco em spawn_blocking | Segurança/parada13/13PASS debug/pacote/imagem; regressões e gates Rust PASS |
| 7. Integração | XMQR↔XMQR, XMQR→Mosquitto e Mosquitto→XMQR; três rotas, metadados, retenção, cadeia, retorno, crash | Local/CI e ELFs do pacote/imagem PASS |
| 8. Distribuição | C149publica client0.43.0/bridge0.5.0, Ubuntu26amd64/rollback, imagem numerada, tag/release imutáveis e seis anexos | PASS; seis downloads/SHA256 e imagem por digest conferidos |

Fonte funcional C148`45ca641b4f6ddd4f230c56d2d5b4704d8fd4e606`:
[registro](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C148-bridge-mqtt5-duravel-percurso.md),
[evidências locais](https://github.com/licodevone/xmqr-client/tree/main/docs/conformance/c148),
[CI](https://github.com/licodevone/xmqr-client/actions/runs/39300031174).
A CI funcional C148 terminou com seis jobsPASS. Os relatóriosdebug/pacote
foram baixados e lidos. A candidata final C149 acrescenta os negativos diretos
e corrige SIGTERM; fonte`9e1d011ffa22aa1225d3775b6fc99a06ae6dfc60`,
[CI39301735099](https://github.com/licodevone/xmqr-client/actions/runs/39301735099)
com seis jobsPASS. Os relatórios da revisão final foram baixados e lidos.
Não confundir a CI anterior com o aceite desta fonte distribuída.
Mosquitto2.0.22 foi fixado por digest nos relatórios.

## Distribuição conferida

[Releaseclient0.43.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.43.0),
[registroC149](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C149-release-0.43.0.md)
e [evidência consolidada](https://github.com/licodevone/xmqr-client/blob/main/docs/conformance/client-release-0.43.0-c149.json).
Tag anotada`61765545258a621b629728cf4e33f0cf2b92b5d3` aponta à fonte9e1d011.
PacoteSHA256`e4d09cec660a0dba20790181727b17c44040913425a3340d3838e45113241f76`.
Seis anexos baixados idênticos; três sidecars remotosPASS. Imagem numerada
`lepinheiro100/xmqr-client:0.43.0`, digest remoto/pull/run dos dois bináriosPASS:
`sha256:9f2f798e49383332d37ac01d5ea98ce1a2056933871e86a98beb03bdd2d10ad6`.
Instalação/rollback descartáveis0.42.1→0.43.0→0.42.1→0.43.0PASS, configuração
preservada e serviçosopt-in. Nenhuma instalação no host do operador.

## Limites do aceite

O contrato é experimental e finito. Não há commit atômico distribuído entre
brokers: uma publicação com resultado remoto incerto pode ser repetida depois
de uma queda. ACK MQTT não comprova processamento de negócio.

A proteção de percurso depende de preservar a propriedade reservada. Um
intermediário que a remove impede essa garantia. MQTT3.1.1 usa manifesto
acíclico; draftv2MQTT5→3.1.1 exige política explícita de descarte de metadados.
V1 mantém seu contrato histórico.

Um voo por rota,1–8rotas e estado até2MiB; burstsQoS0 podem exceder cota.
Expiry é conservador e descarta restante abaixo de1s antes de nova entrega.
Refused preserva obrigação e exige investigação offline; não há comando de
desbloqueio nesta fatia. Migração para formato2 exige diretório e IDs novos,
após drenagem; rollback não apaga nem converte obrigação pendente.

Wire marcou1NOT_RUN: alias/subID não negociados legalmente. A transformação
é testada por unitário; não se anuncia tráfego wire positivo inexistente.
Falhas históricas do runtime e das ACLs da fixture foram preservadas antes das
correções nos prompts/relatórios. Nenhum ESP32, queda de energia, certificação
MQTT5 integral, cluster ou homologação Windows é inferido desses ensaios.

## Checklist do marco

- [x] Prompts C147/C148 antes das funcionalidades e revisões antes de correções.
- [x] Gates e matriz funcional local com falhas anteriores preservadas.
- [x] Guia de configuração, limites, migração e rollback do estado.
- [x] CI da candidata exata completa e relatórios lidos.
- [x] Pacote Ubuntu26amd64, ELFs e instalação/rollback descartáveis aprovados.
- [x] ELF da imagem validado e imagem remota confirmada por digest.
- [x] Tag anotada e seis anexos remotos conferidos.
- [x] Fase8/T02 e plano reconciliados com aceite final P237.
