# P227 — validação integrada da fase 6

Execução em 2026-10-18, Ubuntu26.04/WSL2, Rust1.99/Python3.14.
**EM VALIDAÇÃO: não é fechamento, tag ou release.**

## Proveniência dos primeiros gates

Entrada publicada: broker0.42.0/client0.36.0/admin0.10.0. Binário debug
preexistente do broker era0.41.0: não foi tratado como artefato0.42.0.
Baseline congelado SHA256
`674963f56ab2def9297847a94f5e2388003824eb6d67b75db27e4c7fbbd1709f`.

Candidato integrado com P227A/P227C, sem bump, compilado por
`cargo build --locked --offline --bins -j1` (58,01s). Mudanças funcionais
commitadas em `10bab601050cb547933d6702e4291fe184e86c8d` e `10d5081`.
ELF congelado `../.artifacts/p227-binaries/mqtt-broker-integrated-0.42.0`, SHA256
`46d79faf91220cdd59e43602c8f3528a2654463a6f71408c542a9c8638b4f809`.
Esse candidato modificado não é o artefato publicado da tagv0.42.0. Não houve
alegação de build bit a bit reproduzível entre diretórios/máquinas.

## Resultados efetivamente executados

| Gate | Resultado | Evidência / limite |
| --- | --- | --- |
| Contratos do executor integrado, revisão1.5 | 10PASS;0FAIL,0,098s | `scripts/test_phase6_acceptance.py`, execução nativa WSL |
| VBI MQTT5 | RED2PASS/18FAIL no baseline; GREEN21/21PASS no candidato | [P227A](P227A-fase6-vbi-canonico.md); helper/hashes e cleanup registrados pelo agente |
| Fairness e Will takeover | RED0/3; GREEN3/3PASS,4,972s | [P227C](P227C-fase6-shared-e-will.md); mesmo harness em RED/GREEN |
| Matriz de queda de processo do broker | 12/12PASS no baseline e candidato | QoS1, fasesQoS2, expiração e Will;4cenários×3, SIGKILL só nos filhos próprios |
| Paho MQTT5 P168 | PASS,1,597s no candidato | assignedID,SessionPresent,QoS0/1/2,retained,offline,recusa3.1.1 |
| Paho PLAIN inicial TLS/mTLS | PASS,7,654s no candidato; baseline tambémPASS | pub/subQoS1,senha inválida,método desconhecido; CA/SAN verificados; sem alegação de reauth externa |
| `cargo test --locked --offline -j1` | exit0;263PASS;0FAIL;6ignored | compile96s;lib239PASS/6ignored em43,67s;admin4,main9,integrações11;doc0 |

Relatórios locais sanitizados preservados fora do Git:
`../.artifacts/p227-crash-baseline-1.json`,
`../.artifacts/p227-crash-integrated-1.json`,
`../.artifacts/p227a-vbi-candidate-1.json`,
`../.artifacts/p227c-shared-will-baseline-1.json` e
`../.artifacts/p227c-shared-will-candidate-1.json`.
Os resultados Paho foram observados nos subprocessos exit0; não se anuncia
JSON inexistente desses testes individuais. O executor integrado produzirá
seu próprio relatório exclusivo após construir o conjunto final.

Paho é checkout oficialv2.1.0, commit
`af64a4365c6ac5a7a4d339e7b00f44df91353b35`, usado por PYTHONPATH privado,
sem instalação global/runtime vendorizado. Licenças originais preservadas.
Os seis testes ignorados são campanhas explícitas de fuzz; o gate comum
não equivale a executá-las novamente.

## Pendências que impedem o aceite

- P227D: alias válido ainda não mapeado com tópico vazio deve receber0x82;
  zero/excesso continuam0x94. Matriz registrou a divergência, sem ocultá-la.
- C129: journal inbound do client em clone isolado, ainda sem aceite final
  nem integração na árvore que contém distribuiçãoC128 de outro escritor.
- Repetir fmt/test/Clippy/build/inventário e wire integrados na fonte final,
  com manifests/versões/hashes coerentes e três repositórios limpos.
- Confrontar M01–M10, decisões opcionais e limites de interop com o aceite;
  não marcar fases por contar prompts nem transformar falha externa emPASS.
- Selecionar versões independentes e distribuir somente depois do aceite
  real: commits/push, tags imutáveis, prereleases,deb eHub numerados.

Não foram alterados serviços, firewall, ESP32, segredos ou estado do operador.
Resultados finitos não demonstram perda de energia, SLA, produção ou
certificação completa MQTT5. MIT própria e notices de terceiros preservados.
