# P234 — quadros de dados do client por WS/WSS

Prompt publicado antes da fixture em `a6b6901`; revisões v1.1/v1.2 antecederam
as correções do simulador. Nenhum runtime do client/broker foi alterado.

Cliente usado: ELF do pacote CI 0.42.1, fonte `db844a0808dfa82e436e5b0fe960d66536df4703`,
run `39257417702`. Ubuntu26/WSL, Python3, portas loopback efêmeras, WSS com
certificados temporários CA/SAN/mTLS. Não houve uso de broker/credenciais reais.

Resultado final local: 12/12 PASS, binário inalterado. MQTT 3.1.1/5 em WS e
WSS mTLS: controle binário fragmentado/concatenado recebe uma publicação exata;
CONNACK e PUBLISH enviados como texto provocam fechamento rápido, erro e zero
entrega. O fechamento acontece por iniciativa do receptor; timeout não é PASS.
A fixture usa framing independente do encoder do client. PING/PONG/CLOSE são
controles WebSocket e não entram na proibição de dados de texto.

Preservados: primeira execução 0PASS/12FAIL por chaves bytearray no simulador;
segunda 4PASS/8FAIL por comparação incorreta de JSONL e espera do processo com
socket do servidor ainda aberto. A terceira execução corrigiu apenas o simulador
e passou em 2,701s. Esses FAILs não são reprovas do client nem PASS retroativos.
[Relatórios e hashes](../../docs/conformance/mqtt5-client-websocket-p234.json).

[CI externa da fonte `2972028`](https://github.com/licodevone/xmqr/actions/runs/39259711349):
12/12 PASS. O relatório foi baixado e parseado: binário inalterado e mesmo
SHA-256 do ELF usado localmente. O workflow extraiu o pacote da release 0.42.1
com SHA-256 fixado, sem instalá-lo no host. O resultado local e remoto fecha
a lacuna de evidência MQTT-6.0.0-1 no escopo examinado;
não prova todos os quadros, ataques ou conformidade MQTT integral. Ledgers
P232 permanecem históricos. Sem tag/release do broker por esta prova.

O commit com a fixture foi enviado com supressão da CI geral, pois não alterou
Rust/runtime; o workflow específico foi acionado explicitamente por dispatch
e seu resultado acima é a evidência nova. Não se alega nova execução dos gates
Rust por uma alteração exclusiva do simulador/documentação.
