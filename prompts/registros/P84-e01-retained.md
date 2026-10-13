# P84 — retained físico e verificação wire independente

2026-10-13, Windows/PowerShell, base512e051812e0b672bd83fe18552ee8ff275c1a88,
main limpa. Broker/admin0.11.4, client0.8.1 separado, tarballs preexistentes
preservados. Pedido: continuar paridade funcional Mosquitto e compromisso
anterior de prompts/MIT/testes/commit/push/distribuição de marcos validados.
E01 é dependência de fase2; não iniciar fase3 para contornar placa pendente.

[P84v1.2](../broker/84-e01-retained-observador.md) preparado/apresentado antes
de fontes; revisões antes das correções. Skills xmqr-rust-mqtt/tests/security-review
aplicadas pelo agente principal, sem subagentes; orientaram filas/deadlines,
negativos, distinção console/wire e separação de identidades/chaves do lab.

## Entrega e invariantes

- Firmware opt-in XMQR_E01_RETAINED=1, módulo Rust separado, sem unsafe.
  Default0/P83 preservado e compilado. Cargo observa modo/config/PEMs privados.
- Observer Python wire próprio, independente do codecRust/ESP-IDF, não libmosquitto.
  TLS CA/SAN/validade, certificado/usuário/senha/fingerprint próprios, CleanSession
  e IDs separados. AssinaturaQoS1 observa publicações0/1/2 como entregas0/1/1;
  não captura handshakeQoS2 MCU↔broker. C43/Mosquitto externo é evidência separada.
- Novo caso privado exclusivo, CA/servidor/board vigentes reutilizados sem
  alterar originais. Broker mount só CA pública/certificado/chave do servidor/
  users/ACL; nunca chaves de CA/board/observer. Cert observer3dias respeita CA.
- ACL board: publish bytes/retained; subscribe bytes/control. Observer: subscribe
  bytes/retained, publish só control. Sem wildcard/nova permissão para outros tópicos.
- Após loopbacks, board publica retainedQoS1 seq3/4 com1024bytes, espera PUBACK;
  nova sessão observa RETAIN1/QoS1/últimosbytes e só então confirma em MQTT.
  Board espera confirmação específica15s. Retained vazio remove valor; sessão
  nova exige ausência2s + PINGRESP vivo antes de confirmar5. EOF/TLS/ACK errado
  não equivalem a ausência; ACK não significa sucesso de aplicação de negócio.
- Observer packet4096/framebudget32/fila32, IDs/deadlines finitos e prazo da coleta
  compartilhado nas operaçõesMQTT. Parser ASCII fechado/tetos/ordem estendidos;
  sequence antiga/missing/FAIL/duplicata/modo errado veta aceite. Console E wire
  completos necessários; só um não aprova. Auto-reconnect permanece desativado.
- Backup original duas leituras4MiB iguais, COM4/CH340/ESP32 previamente conferido;
  app997488<1048576bytes, bootloader/tabela SDK reais, flash verificado duas vezes.
  Sem force/erase geral/NVS/efuses/GPIO, firewall/roteador ou serviço real alterado.

## Gates/resultados reais

| Gate | Resultado |
| --- | --- |
| Primeira suíte antes de flash |78executados/77PASS/1SKIP Windows, saída0 |
| Negativos adicionais |80executados; um erro no double Mock sem spec de método assert_no_replay; FAILED, não falha MQTT |
| Revisãov1.1/correção do teste |80executados/79PASS/1SKIP Windows;64subset WSL PASS |
| Revisãov1.2/metadados | Primeiro report usava rótuloP82/lista remaining antiga; preservado e corrigida finalização no código antes do novo ensaio |
| Provas contra falso aceite | Console positivo sozinho → FAIL_OBSERVER; wire positivo/console incompleto → FAIL_INCOMPLETE; sem remover pendências |
| Suíte final |83executados/82PASS/1SKIP Windows, saída0; symlink real sem privilégio host |
| Subset WSLUbuntu26/Python3.14 |64PASS/0SKIP, saída0, inclui symlink real; mocks não são testes de rede física |
| Fmt/build release locked/Clippy -D warnings | PASS com modos0 e1; firmware final de modo1 |
| Inventário fixture |146declarações/PASS, Cargo.lock/dependências intactos |
| Prep privado | originais preservados/observer só publica control/mount sem device keys:TRUE |
| Primeiro físico |PASS_RETAINED_SLICE,6verificações wire,0violações,0erros cleanup, saída0; metadados antigos detectados |
| Físico final |PASS_RETAINED_SLICE,6verificações wire,0violações,831bytes/11linhas descartadas sem conteúdo, saída0 |
| Cleanup final | container/volume próprios ausentes; lab não mantém broker permanente |

Datas UTC, hashes host/source/harness, sequência final e backup no
[JSON sanitizado](../../docs/results/p84-e01-retained-2026-10-13.json).
Hash harness concatena basename+bytes, na ordem documentada no JSON. Hashes
retrataram arquivos do host durante execução, não commit futuro nem attestation
ELF↔Git; cfg1 explicitamente selecionado e binário privado não distribuído.
Os relatórios anteriores/private cases foram preservados, não reescritos.

Os seis resultados wire: bytes0/1/2, replayseq3, replayseq4, exclusão observada.
Desconexão após testes ocorre no wifi.stop() explícito, não prova reconexão/Will.
NúcleoRust111 broker/54client não reexecutado: não houve mudança nesses runtimes;
build/Clippy do crate ESP e testes de host foram reexecutados. cargo test no
targetESP32 não é executável por runnerhost; usar hardware e testes do harness.

## Cobertura e limites

OASIS §3.3.1.3/MQTT-3.3.1-5/6/8/10/11 fundamenta retained positivo observado.
Entregas live com RETAIN0 em update/delete (§-9), retained após restart,
Will, reconexão/backoff/duplicatas, negativos físicos TLS/ACL/credenciais,
heap e cliente terceiro/handshakeQoS2 MCU ainda NOT_RUN. Ausência2s+PING é
observação limitada com broker vivo, não prova longa/durável/energia. Observer
próprio não equivale a biblioteca cliente independente completa ou conformidade.
[OASIS](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html#_Toc398718038),
[esp-idf-svc](https://github.com/esp-rs/esp-idf-svc/blob/master/src/mqtt/client.rs).

Código próprio MIT; licenças146pacotes/SDK/toolchain permanecem próprias.
Revisão de segurança limitada a esta fatia: identidades separadas, TLSsemfallback,
ACL mínima, limites/guards e logs sanitizados; não declarar segurança integral.
Diretório privado/ACL do operador é fronteira de confiança, não defesa contra
atacante local já capaz de editar esse diretório durante preparação/execução.

Fase2/E01 PARTIAL, sem fase3/produção. Firmware diagnóstico fica na placa;
ele se encerra e não mantém comunicação após STOP. Senhas/chaves/JSONprivado/
ELF/bin/target/backup/logs completos não publicados. Runtime/versões permanecem
0.11.4/0.8.1; sem nova tag/release/deb/Hub para fixture-only. Marcos existentes
imutáveis; distribuição de próximo runtime validado mantém autorização.
Commit/push de fonte/docs/prompt sanitizados após auditoria, SHA real na entrega.
