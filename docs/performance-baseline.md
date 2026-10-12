# Baseline P62 — RAM, CPU e PUBACK QoS1

Medição em 2026-10-11, broker0.11.0. Primeira fatia da fase2, sem mudança runtime.

## Ambiente e método

CPU: Intel(R) Core(TM) Ultra 7 155H; 3 CPUs lógicas visíveis noWSL. Kernel 6.18.33.2-microsoft-standard-WSL2; Rust rustc 1.99.0 (b940084d7 2026-09-28); Python3.14.4. Memória visível: 7.76GiB.

FonteHEAD: d7b9d413167d85b9ce8ceb1a42eca4022e72422b. Binário otimizado SHA-256: bd0d101b18804d475b0df386aff6e97e7d9b6922f38ba0a60d70f80a2d21dcbb. Filesystem reportado porstat: ext2/ext3 (nativeWSL).

Processos próprios em loopback open-lab, defaults, semTLS/ACL/monitor. Diretórios temporários no /home nativo, removidos no fim. Três repetições e processo novo por cenário. Conexões ociosas:0,5s de estabilização e1s de medição. QoS1:100 mensagens de warmup,2000 medidas, payload256 com sequência variável eRETAIN; um publicador aguardaPUBACK específico antes da mensagem seguinte.

RSS amostrado a cada20ms; HWM é do tempo de vida, incluindo startup. CPU é delta de utime+stime do broker, não do gerador, com100% igual a um núcleo. Percentis nearest-rank por repetição. Instalação/estado reais não usados.

## Conexões ociosas

| Conexões | RSS mediano entre repetições (MiB) | Faixa do RSS mediano (MiB) | CPU medida |
| --- | --- | --- | --- |
| 1 | 5.51 | 5.38–5.51 | abaixo da resolução de ticks nesta janela |
| 8 | 5.66 | 5.43–5.66 | abaixo da resolução de ticks nesta janela |
| 32 | 6.01 | 5.87–6.04 | abaixo da resolução de ticks nesta janela |

Não interpretar0 ticks como CPU absolutamentezero. Três processos novos não permitem estimar RAM marginal por cliente com precisão: allocator, startup e ruído variam.

## Publicador sequencial QoS1 + retained

| Repetição | Janela (s) | Mensagens/s | Média (ms) | p50 (ms) | p95 (ms) | p99 (ms) | CPU (% de1núcleo) | RSS mediano (MiB) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 8.77 | 228.0 | 4.381 | 4.160 | 5.181 | 8.811 | 4.56 | 5.70 |
| 2 | 9.42 | 212.3 | 4.708 | 4.374 | 6.512 | 14.450 | 4.25 | 5.64 |
| 3 | 10.38 | 192.7 | 5.187 | 4.824 | 6.579 | 15.667 | 4.05 | 5.70 |

Taxa média entre repetições: 211.0 mensagens/s; desvio padrão amostral 17.7; faixa 192.7–228.0. Percentis não foram combinados entre repetições.

Este número é taxa de confirmação sequencial desta carga, não throughput máximo. PUBACK não mede entrega/consumo por assinante. Há trabalho durável, mas o teste não prova resistência a perda de energia ou desempenho de outro disco.

## Ensaio preliminar e limites

Ensaio inicial com200 mensagens e /tmp(tmpfs) concluiu, mas janelas de19–25ms eram inadequadas para CPU e não representavam disco. Seus números não são usados nesta tabela. O prompt foi revisado antes de ampliar amostra/alterar armazenamento e adicionarretained variável. O timestamp original rotulado started_utc era do fim; a cópia abaixo corrige apenas o nome para completed_utc, preservando números e hash do harness usado.

FaltamTLS/mTLS, fan-out, QoS0/QoS2, conexões em criação simultânea, subscribers lentos, filas/retained bootstrap e saturação. Não aumentar quotas com base nesta baseline. WSL e concorrência de outros programas afetam resultado. Sem comparação de desempenhoMosquitto nesta entrega.

## Reproduzir

```sh
python3 -B scripts/benchmark_baseline.py --broker target/release/mqtt-broker \
  --state-root /home/SEU_USUARIO --report target/p62-nova-medicao.json
```

Usar binário release da versão0.11.0 e relatório novo: o script recusa sobrescrever. Exige Linux/proc e Python compatível; nenhum serviço instalado será operado.

[Resultados JSON](results/p62-baseline-2026-10-11.json) · [Prompt](../prompts/broker/62-baseline-capacidade.md) · [Registro](../prompts/registros/P62-baseline-capacidade.md)

Próxima fatia sugerida: comparar QoS0/1/2 e fan-out, com warmup/janela/repetições eTLS, antes de profiling/otimização. Prompt próprio antes do código.
