# P72 — QoS, fan-out e mTLS

Campanha de 2026-10-12 no broker 0.11.2. 36 cenários aprovados, com 10.800
publicações medidas e 48.600 entregas verificadas; warmup excluído dessas contagens.
Todos os processos e estados eram temporários, sem operar serviços instalados.

## Método

Intel Core Ultra 7 155H, 3 CPUs lógicas visíveis ao processo, Ubuntu26/WSL2,
kernel 6.18.33.2-microsoft-standard-WSL2 e Python 3.14.4. Estado em filesystem
nativo ext2/ext3 sob /home, não no volume Windows. Binário release, versão e
SHA-256, fonte HEAD e hashes dos scripts registrados no JSON.

Matriz: open-lab e secure-mtls × QoS0/1/2 × 1/8 assinantes × 3 repetições.
Cada cenário usa processo novo, 20 mensagens de warmup e 300 medidas, payload
256 bytes com sequência, sem retained. Publicação sequencial: aguarda ACK do
publicador, quando aplicável, depois verifica tópico/payload/sequência/QoS de
todos os assinantes e envia seus ACKs. QoS2 completa PUBREC/PUBREL/PUBCOMP nas
duas direções. Barreira PING ao fim drena ACKs antes de DISCONNECT/SIGTERM.

Latência mede publicação até recepção wire por todos os assinantes e troca de
ACKs indicada acima. Não mede processamento de negócio nem espera de confirmação
de gravação do último ACK enviado pelo assinante. TCP_NODELAY não é ativado pelo
harness; a política TCP do broker permanece a da versão medida. Handshake TLS,
autenticação e SUBSCRIBE acontecem antes da janela de medição.

RSS amostrado a cada20ms; CPU por delta de ticks do broker, 100% representa um
núcleo. Percentis nearest-rank por repetição. Mediana abaixo é entre três taxas
ou RSS medianos; percentis não são misturados. O JSON contém p50/p95/p99, CPU,
RSS/HWM, contagens e duração por cenário. CA e senha incorretas foram recusadas,
seguindo-se uma conexão válida. CA/SAN e certificado cliente são verificados.

## Resultados

| Transporte | QoS | Assinantes | Publicações/s, mediana | RSS mediano (MiB) | p95 entre repetições (ms) |
| --- | --- | --- | --- | --- | --- |
| open-lab | 0 | 1 | 205,3 | 5,77 | 5,52–6,22 |
| open-lab | 0 | 8 | 198,1 | 5,93 | 6,13–7,75 |
| open-lab | 1 | 1 | 96,9 | 5,84 | 11,54–15,80 |
| open-lab | 1 | 8 | 20,9 | 6,14 | 54,79–72,20 |
| open-lab | 2 | 1 | 45,4 | 5,82 | 29,06–30,85 |
| open-lab | 2 | 8 | 9,6 | 6,19 | 127,29–130,15 |
| mTLS | 0 | 1 | 181,9 | 26,68 | 6,12–7,33 |
| mTLS | 0 | 8 | 172,7 | 26,97 | 6,15–7,74 |
| mTLS | 1 | 1 | 89,5 | 26,78 | 11,89–14,14 |
| mTLS | 1 | 8 | 20,7 | 27,29 | 53,14–64,78 |
| mTLS | 2 | 1 | 49,0 | 26,73 | 23,92–30,56 |
| mTLS | 2 | 8 | 10,4 | 27,35 | 113,54–149,10 |

## Limites e reprodução

As taxas são desta carga sequencial com conferência de cada entrega, não
throughput máximo. Outros trabalhos, incluindo gates/build do client, rodaram
no mesmo host durante parte da campanha. Há variação de RSS/latência entre
repetições; não usar a diferença entre transportes como custo isolado de TLS.
Não comparar diretamente à P62: ela mede PUBACK QoS1 retained sem assinantes.
Ainda faltam saturação, assinantes lentos, conexões simultâneas e ESP32; a fase2
permanece aberta. Não ampliar quotas com base nesta campanha.

```sh
python3 -B scripts/test_benchmark_fanout.py
python3 -B scripts/benchmark_fanout.py \
  --broker target/release/mqtt-broker --admin target/release/mqtt-admin \
  --state-root /home/SEU_USUARIO --report target/p72-nova-campanha.json
```

Linux /proc, pty, Python3.11+, OpenSSL e binários broker/admin são necessários.
O harness importa fixtures de certificados do projeto vizinho xmqr-client;
o gerador de tráfego é wire independente da CLI. Relatório existente é recusado;
diretórios privados/certificados/senha de teste são criados e removidos pelo ensaio.

[JSON completo](results/p72-fanout-2026-10-12.json) ·
[Prompt](../prompts/broker/72-capacidade-qos-fanout-mtls.md) ·
[Registro](../prompts/registros/P72-capacidade-qos-fanout-mtls.md)
