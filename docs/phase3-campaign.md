# P91 — pressão, recuperação e MQTT 3.1.1 externo

Campanha preparada em 2026-10-13. Enquanto gates do candidato não estiverem
registrados, esta página não declara B08 nem a fase 3 concluídos.

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
`scripts/test_phase3_harness.py`:13testes determinísticos da contabilidade,
incluindo DUP permitido emQoS1, falta lógica e duplicação proibida emQoS2,
e preservação do primeiro erro quando outro cenário é cancelado em paralelo.
Incluem QoS0/DUP e negativos do helper diagnóstico: nunca ready, erro persistente
mesmo ready1 e resposta ready1 posterior ao prazo. O helper não substitui o
oráculo strict de saúde do ensaio prolongado; três reprobes após ready0 servem
apenas para registrar diagnóstico, não para transformar FAIL em PASS.

`scripts/test_phase3_tls_shutdown.py`:10casos de EOF TLS estrito em TLS1.2/1.3,
com `suppress_ragged_eofs=False`:2controles DISCONNECT normal,6SIGTERM e2SIGTERM
com handshake incompleto paralelo. O socket incompleto permanece aberto até o
processo terminar, enquanto a conexão autenticada deve receber close_notify.
Conferir exit0 e budget compartilhado15s (+.5s tolerância de observação).
O relatório usa SHA da cópia privada realmente executada, não de arquivo que
possa ter sido recompilado durante o ensaio. Certificados/estado só sintéticos.

## Reprodução

Executar na raiz deste broker Linux/WSL com os binários aceitos:

```text
python3 scripts/test_phase3_harness.py
python3 scripts/test_phase3_wire.py --broker target/release/mqtt-broker --label candidate --report CAMINHO-NOVO/wire.json
python3 scripts/test_phase3_tls_shutdown.py --broker target/release/mqtt-broker --admin target/release/mqtt-admin --state-root /var/tmp --label candidate --report CAMINHO-NOVO/tls-shutdown.json
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

## Limites e fonte

Recuperação de processo não é perda física de energia. Pressão escolhida não
mede teto de produção, SLA ou estabilidade de dias. Não homologa Windows
backend, arm64, MSRVexato, rotação TLS, MQTT5 ou firmware ESP32 novo. O fechamento
da fase é coordenado com B06/B07/C07 e distribuição do commit aceito.

Fonte normativa consultada:
[OASIS MQTT3.1.1 com Errata01](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/errata01/os/mqtt-v3.1.1-errata01-os-complete.html),
especialmente capítulos1.5/2.2/2.3/3.1–3.14/4.3/4.4/4.7. Não há alegação de
auditoria exaustiva de todas as cláusulas por estes19vetores.
