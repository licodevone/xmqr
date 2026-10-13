# P91 — pressão, recuperação e MQTT 3.1.1 externo

Campanha executada em 2026-10-13. Gates P91 finais PASS no candidato descrito
abaixo. Esta evidência cobre B08; o fechamento global da fase 3 e a publicação
dependem também dos gates B06/B07/C07 e da distribuição coordenada.

## Resultado final observado

Broker nativo SHA256
`e57b1e2d26de50d09bb6bdadb74e4c0531dcac15399ece4369f4e0a0824e2987`;
admin legado `f40ecbb5e1641565bbf6ec2cb0e14a7d58973709270bc89c64070ae32b6f9083`.
TLS estrito: 12/12; protocolo wire: 19/19; contratos do harness: 21/21 PASS.

Soak 6/6 PASS: **1808.946s de parede** (30min8.946s), TCP e mTLS paralelos em
cada uma das três repetições independentes. Publicações/entregas da tabela são
do tráfego live; operações offline/retained/replay são verificadas separadamente.

| Repetição | Transporte | Duração real (s) | Publicações de 1 KiB | Entregas fan-out 4 | Pico RSS (KiB) |
|---|---|---:|---:|---:|---:|
| 1 | TCP | 604.218 | 6744 | 26976 | 7368 |
| 1 | mTLS | 604.617 | 5904 | 23616 | 48520 |
| 2 | TCP | 601.218 | 6936 | 27744 | 7312 |
| 2 | mTLS | 601.088 | 6096 | 24384 | 48340 |
| 3 | TCP | 600.914 | 7776 | 31104 | 7392 |
| 3 | mTLS | 601.264 | 7056 | 28224 | 29152 |

Totais live: 40512 publicações/162048 entregas, 90 crashes e 30 SIGTERM. Cada
cenário final: ready=1/errors=0; conexões, sessões, offline, inflight, filas e
retained=0. Os 1698 probes de saúde foram preservados: quatro ready=0
transitórios, pior recuperação de 1.659s, sempre processo vivo e zero erros;
não se alega SLA instantâneo de 500ms. Pico de arquivos duráveis: 890870 bytes
(<128MiB). Maior crescimento RSS observado por geração: 792KiB TCP/1448KiB
mTLS em janelas de aproximadamente 120s; não prova ausência
universal de vazamentos nem estabilidade de dias.

Interop 87/87 PASS em 346.063s: 59 regressões C43 inalteradas (Mosquitto -W8),
28 extensões em ambos os brokers e sentidos, mTLS, retomada SIGTERM,
retained-crash, idle e negativos ACL com prova explícita. Cleanup de 202
containers/2 volumes PASS.
BrokerDocker0.11.6ID`sha256:576de5ddc2dc2f74cbb2f243126d8c36668784f110ed0da03a05df8435352f97`
(runtime commit`abbe38ca6c041f7328e85054506a4eed22c74c41`),
client0.9.0ID`sha256:e1c56183bd98fbe33c9fade58f81d61b2f60eb960c3704747528ec7f471a11ed`
(commit`e688c75a3779803e8f1868792dcc5e7a36f2dd6e`), Mosquitto2.0.22ID
`sha256:199ea8ef2e35ec2b1b37e59cfd1dbae538ed4dfa4a2251a121a52215a6248a21`.
Will/crash isolado6/6 PASS em26.457s, entrega exata nos dois sentidos até2.795s,
exit0; sem aumentar-W8. É diagnóstico adicional, não substitui matriz completa.

Reports finais sanitizados em `../.artifacts/`:
`p91-soak-candidate-6.json`, `p91-interop-candidate-4.json`,
`p91-tls-eof-candidate-2.json`, `p91-tls-no-connect-candidate-1.json`,
`p91-wire-candidate-3.json`; diagnóstico `p91-will-diagnostic-1.json`.
Todos os FAIL históricos permanecem FAIL; primeiras tentativas interop72/18
tinham telemetria insuficiente e suas causas exatas não foram comprovadas.
Nenhuma mudança de core foi atribuída a essas duas falhas sem prova.

## Método e scripts

`scripts/phase3_soak.py`: Linux/WSL, binários explícitos, cópia temporária
imutável do broker, estado em filesystem Linux privado e monitor loopback.
Três repetições de >=600s; TCP e mTLS simultâneos em instâncias distintas dentro
de cada repetição. Mínimo 30 minutos de parede e 60 processo-minutos, não dias.
Fan-out4, QoS0/1/2, payload1024 com sequência/hash, sessões offline, retained,
SIGTERM/restart, SIGKILL após PUBREC inbound e após PUBREL outbound.
OutboundQoS1 também interrompe antes de PUBACK e exige mesmoID/bytes/DUP ao
reconectar, sem confundir duas observações com duas mensagens lógicas. O tráfego
é contínuo entre conjuntos de recuperação separados por120s. Cada conjunto
de entregas verifica sequência, bytes, QoS, identificadores e flags; QoS2 offline
em lote admite múltiplos PUBLISH antes de PUBREL, conforme protocolo.

Budgets de segurança do ensaio: 256MiB RSS,128MiB arquivos duráveis, no máximo
2000 amostras por cenário,4destinatários e5conexões normais. Preservadas quotas
do broker: offline64/inflight32/sessões64/retained256. Samples não são heap exato;
registrar delta/amostras por geração, pois RSS antes/depois de restart não prova
ausência de leak. Counters do monitor reiniciam em cada processo: não confundir
counters finais com o total de operações acumuladas no harness.

`scripts/verify_phase3_interop.py`: usa C43/Mosquitto2.0.22 com IDs de imagens
existentes, sem pull/instalação. Reexecuta os59cenários C43 e acrescenta retomada
de assinante persistente após SIGTERM, retained após SIGKILL, observação
independente de ACL negada e espera ociosa superior ao deadline de protocolo.
Clientes XMQR e Mosquitto em ambos os sentidos, nos dois brokers, sempre mTLS.
QoS1 pode retransmitir: validar o conjunto lógico de payloads, sem exigir
exatamente uma entrega. Mosquitto tem contrato de persistence diferente:
retained-crash espera autosave explícito, não interpreta PUBACK como fsync.
Containers/volumes com nonce, nonroot, filesystem readonly, caps-none,
namespace loopback compartilhado e nenhuma porta publicada no host.
Na extensão, namespaceholder independente permanece ativo durante restart de
broker; compara namespaceantes/depois. O-W40doMosquitto é lifetime total
somente da extensão; C43mantém-W8. O gateidle do XMQR também proíbe marcador
de retry, evitando aceitar timeout disfarçado por reconexão automática.

`scripts/test_phase3_wire.py`:19cenários wire independentes vinculados às
cláusulas: ClientID vazio, flags, UTF-8, IDs zero, QoS0/DUP, QoS reservado,
filtro inválido, keepalive1s, CONNECT fragmentado e PING concatenado.
`scripts/test_phase3_harness.py`:21testes determinísticos da contabilidade,
incluindo DUP permitido emQoS1, falta lógica e duplicação proibida emQoS2,
e preservação do primeiro erro quando outro cenário é cancelado em paralelo.
Incluem QoS0/DUP e negativos do helper diagnóstico: nunca ready, erro persistente
mesmo ready1, resposta ready1 posterior ao prazo, processo morto antes/durante
probe e troca de PID. P91v1.22 adotou recuperação saudável em até15s somente
após tráfego quiescente, depois de comprovar ready0→1/.103s/zeroerrors com
conclusão do último disconnect/commit. Mesmo processo deve estar vivo antes e
depois de cada probe, ready1 dentro do deadline absoluto, zero erros persistentes
em todos os probes. Todos os probes/tempos/counters são registrados (cap4000,
exceder é FAIL), também na leitura final; tempo de espera integra a duração real
e o deadline total solicitado+45s. As tentativas strict anteriores seguem FAIL.
Os negativos de assinatura também distinguem SUBACK recusado de exit arbitrário,
TLS/timeout/CONN_LOST, exit inesperado e evidência contraditória. Recusa exige
SUBACK128/Mosquittoexit0 ou erro SUBACK explícito/XMQRexit1; filtragem de entrega
exige assinatura confirmada, processo vivo e writer independente autorizado,
sem DATA não autorizado. Nenhum erro de transporte é aceito como prova de ACL.

`scripts/test_phase3_tls_shutdown.py`:10casos de EOF TLS estrito em TLS1.2/1.3,
com `suppress_ragged_eofs=False`:2controles DISCONNECT normal,6SIGTERM e2SIGTERM
com handshake incompleto paralelo. O socket incompleto permanece aberto até o
processo terminar, enquanto a conexão autenticada deve receber close_notify.
Conferir exit0 e budget compartilhado15s (+.5s tolerância de observação).
O relatório usa SHA da cópia privada realmente executada, não de arquivo que
possa ter sido recompilado durante o ensaio. Certificados/estado só sintéticos.

`scripts/test_phase3_tls_no_connect.py`:2casos TLS1.2/1.3, handshake completo
validado por CA/SAN, sem enviar qualquer byte MQTT, depois SIGTERM. A conexão
TLS estabelecida ainda não é uma sessão MQTT autenticada. Exige igualmente EOF
limpo/exit0/prazo15.5s, cobrindo o caminho anterior ao primeiro CONNECT.

`scripts/test_phase3_will_diagnostic.py`:subset baseline isolado, política e
fixture C43/persistencefalse/W8 originais, três repetições de ambos sentidos,
linha temporal real recipientReady→sourceReady→SIGKILL→entrega. Não é aceite
do candidato, não transforma um FAIL anterior de causa desconhecida em PASS.

## Reprodução

Executar na raiz deste broker Linux/WSL com os binários aceitos:

```text
python3 scripts/test_phase3_harness.py
python3 scripts/test_phase3_wire.py --broker target/release/mqtt-broker --label candidate --report CAMINHO-NOVO/wire.json
python3 scripts/test_phase3_tls_shutdown.py --broker target/release/mqtt-broker --admin target/release/mqtt-admin --state-root /var/tmp --label candidate --report CAMINHO-NOVO/tls-shutdown.json
python3 scripts/test_phase3_tls_no_connect.py --broker target/release/mqtt-broker --admin target/release/mqtt-admin --state-root /var/tmp --label candidate --report CAMINHO-NOVO/tls-no-connect.json
python3 scripts/phase3_soak.py --broker target/release/mqtt-broker --admin target/release/mqtt-admin --state-root /var/tmp --label candidate --seconds 600 --repetitions 3 --report CAMINHO-NOVO/soak.json
```

O teste externo usa Docker Desktop CLI no Windows e OpenSSL disponível:

```text
python scripts/verify_phase3_interop.py --broker-image IMAGEM-CANDIDATA-BROKER --client-image IMAGEM-CANDIDATA-CLIENT --hash-file HASH-PUBLICO-TESTE --openssl OPENSSL --label candidate --report CAMINHO-NOVO/interop.json
```

O hash é da senha pública `fixture-pass`, nunca de credencial real. Os
certificados/chaves/credenciais/estado temporários não são anexos de release.
Reports exclusivos incluem SHA256, tempos, cenários, status e cleanup. Baseline
da versão anterior é identificada como baseline, não aceita código futuro.
O state-root deve ser Linux disk-backed, não tmpfs/DrvFS, com>=512MiB livres.
Nesta sessão `/tmp` estava tmpfs100% e abortou ensaios; usar `/var/tmp`ext4
comprovado. Nenhum arquivo de outros processos foi apagado para liberar espaço.

## Checkpoint anterior a P95

O candidato d371d283 passou19wire e59C43, mas falhou na extensão SIGTERM/mTLS:
Mosquitto_sub exit7(CONN_LOST), sem timeout e sem reconexão bem-sucedida. A prova
direta baseline2 confirmou2controles PASS e8SIGTERM FAIL com EOF TLS truncado,
apesar do brokerexit0. Esses FAIL ficam preservados e motivaram correção P95
no core, por outro agente. A campanha600x3 completa e a matriz87casos continuam
pendentes no binário/imagem posteriores a essa correção; resultados antigos
não aceitam o código corrigido.

O primeiro candidato P95(69ec47dc) passou10EOF TLS e19wire, mas a revisão
posterior demonstrou EOF truncado em2/2TLS estabelecidos sem CONNECT. Correção
adicional pertence ao P95; todos os gates finais devem usar o próximo SHA.
Seu soak strict também falhou268.599s e registrou o transiente de saúde citado
acima, sem erro de persistência e com filas vazias depois da recuperação. Essa
evidência fundamenta o contrato quiescente limitado, não uma alegação de SLA.

## Limites e fonte

Recuperação de processo não é perda física de energia. Pressão escolhida não
mede teto de produção, SLA ou estabilidade de dias. Não homologa Windows
backend, arm64, MSRVexato, rotação TLS, MQTT5 ou firmware ESP32 novo. O fechamento
da fase é coordenado com B06/B07/C07 e distribuição do commit aceito.

Fonte normativa consultada:
[OASIS MQTT3.1.1 com Errata01](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/errata01/os/mqtt-v3.1.1-errata01-os-complete.html),
especialmente capítulos1.5/2.2/2.3/3.1–3.14/4.3/4.4/4.7. Não há alegação de
auditoria exaustiva de todas as cláusulas por estes19vetores.
