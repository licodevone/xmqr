# P72 — capacidade QoS/fan-out/mTLS

2026-10-12. [Prompt rev1/rev2](../broker/72-capacidade-qos-fanout-mtls.md) criado antes
do harness. Base broker b47e063/0.11.2, client 0.7.1; trabalho P71 e arquivos
Docker/P68 preservados. Aplicada skill xmqr-tests, sem subagentes.

PASS: 4 contratos negativos do harness (sequência, ACK, handshake bidirecional
QoS2, argumentos/relatório existente). Smoke: 12 cenários, 10 mensagens por
cenário, warmup1, repetição1; arquivo target/p72-smoke.json.

PASS: campanha com defaults, 36 cenários, 10.800 publicações medidas e 48.600
entregas verificadas, 3 repetições. Broker --version confirma0.11.2; SHA-256
idêntico antes/depois. Wrong CA/wrong password recusadas e conexão válida
posterior aprovada. Processos encerrados SIGTERM/exit0, ACKs drenados por PING,
diretórios temporários removidos. Comandos executados via Ubuntu26/WSL:

```sh
python3 -B scripts/test_benchmark_fanout.py
python3 -B scripts/benchmark_fanout.py --broker target/release/mqtt-broker \
  --admin target/release/mqtt-admin --state-root /home/licod26 \
  --report target/p72-campaign.json
```

Relatório copiado sem modificar medições para docs/results; resumo em
[performance-fanout.md](../../docs/performance-fanout.md). Hashes, CPU/kernel,
parâmetros, latências, RAM/CPU e contagens constam no JSON. Gates/build do client
no mesmo host durante parte da campanha são limitação explícita, sem conclusão
de custo isolado TLS, capacidade máxima ou produção. Fase2 permanece aberta.

NOT_RUN: gates Rust broker, pois não houve alteração runtime/manifests; binário
aceito P64 é a base do ensaio. Saturação, filas lentas e ESP32 ainda pendentes.
PASS: links locais e git diff--check. Gate suplementar de inventário inicialmente
BLOCKED por Cargo fora do PATH no shell sem perfil; rev2 precedeu ajuste do PATH.
PASS após ajuste: inventário MIT/dependências coincide e4 contratos do harness.
Não criada versão vX.Y.Z por benchmark; o marco funcional client é independente.
Checklists atualizados somente para entregas com aceite. Publicação/commit sob
autorização do pedido atual; hashes de commits finais não são presumidos.

## Publicação do marco

Commit cf0c99c publicado em main: harness, relatório e checklist P71/P72.
Sem nova tag de versãobroker: runtime permanece0.11.2. Client publicou
[tag/prerelease0.8.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.8.0)
no commit8cd0e1c, com gates e artefatos descritos no registroC41.
