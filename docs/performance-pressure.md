# P80 — capacidade, saturação e clientes lentos

2026-10-13:60cenários PASS no broker/admin0.11.4 candidato. Relatório:
[JSON com hashes e resultados](results/p80-pressure-2026-10-13.json).
HEAD no JSON é a base anterior ao commit; binário e harness estão identificados
separadamente porSHA256. Artefatos de release exigem repetição no commit exato.

## Método

Intel CoreUltra7 155H,3CPUs lógicas, Ubuntu26/WSL2, Rust1.99, Python3.14.4,
kernel6.18.33.2-microsoft-standard-WSL2. Estado temporário em /home nativo;
stat identifica filesystem ext2/ext3. MonitorHTTPloopback ligado; RSS20ms,
CPU por ticks (100%=1núcleo), percentis nearest-rank por repetição.
Processo novo por cenário,3repetições emTCPopen-lab/mTLS.

- 24ensaios de admissão: burstN1/8/32/64, N+1 recusado e vaga reutilizada.
  Retry de criação limitado45s; mTLS até4hashesArgon2 concorrentes.
- 6ensaios sem primeiros bytes: fechamento cerca3s e nova conexão aceita.
- 24ensaios QoS1/2 sem ACK do assinante: inflight/offline4/8 e32/64,
  aceita12/96 antes da recusa, outros clientes progridem, restart/drain íntegros.
  ExcessoQoS1 semPUBACK; QoS2 pode terPUBREC durável mas nãoPUBCOMP até espaço
  disponível. Após restart, ownershipQoS2 pendente é concluído.
- 6não leitoresQoS0: payload4096, SO_RCVBUF4096, batches32, teto5000/60s;
  fechamento, publicador independente e reutilização da vaga no teto3conexões.

## Admissão: faixas entre três repetições

| Transporte | N | RSS mediano (MiB) | p95 conexão (ms) |
| --- | --- | --- | --- |
| TCP |1|5,59–5,68|7,00–8,23|
| TCP |8|5,77–5,82|41,44–47,91|
| TCP |32|6,13–6,24|132,77–173,05|
| TCP |64|6,70–6,77|281,32–344,34|
| mTLS |1|26,55–26,56|53,43–69,02|
| mTLS |8|83,84–83,91|191,36–229,49|
| mTLS |32|84,82–103,76|379,10–579,81|
| mTLS |64|104,68–104,77|764,66–1018,12|

mTLS:0/12/172/656retries de criação somados paraN1/8/32/64;
latências incluem retries. Não são mensagens perdidas de sessão aceita.
Argon2/allocator elevamRAM no burst; não inferir custo linear por conexão.

Não leitor fechado:TCP4,66–5,08s, mTLS7,70–8,02s desde o início do fluxo.
PUBACKp95 independente:TCP5,76–7,65ms, mTLS5,44–7,91ms.
Todos os p50/p95/p99, CPU, RSS/HWM, contagens e durações estão no JSON.

## Defeito corrigido e limites

0.11.3 podia remover a sessão mas ficar presa em shutdownTLS/flush sem prazo:
smoke mTLS atingiu5024tentativas, sessions2/connections_active3. Patch0.11.4
limita shutdown3s; depois descarta a conexão sem prometer flush concluído.
Duas regressões de transporte e duas do ator cobrem deadline, fila64,
progressão do peer e ausência de fan-out/retained parcial na recusa.

64 é o teto configurado exercitado, NÃO throughput/capacidade máxima de produção.
Janelas curtas não provam memória estável indefinidamente, fairness sustentada,
queda de energia ou SLA. Monitoramento/WSL e trabalhos concorrentes afetam
resultados; P62/P72 têm outros métodos. Zero ticks não significa CPUzero.
ACK é protocolo, não confirmação de negócio. MIT/dependências/quotas preservadas.

[ADR quotas por identidade](architecture/adr-0006-identity-quotas.md).
[Aceite globalfase2](phase2-acceptance.md) continua dependente de placa real.

## Reprodução

Executar python3 -B scripts/test_benchmark_pressure.py; depois
python3 -B scripts/benchmark_pressure.py --broker target/release/mqtt-broker
--admin target/release/mqtt-admin --state-root /home/SEU_USUARIO
--report target/p80-nova-campanha.json (argumentos na mesma linha).
Exige Linux/proc/OpenSSL; relatório existente/symlink recusado; recursos
privados são criados/limpos só no ensaio, nunca na instalação do operador.
