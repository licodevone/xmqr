# P62 rev1 — primeira medição de capacidade

Base d7b9d41/tagv0.11.0, fase1 aceita; confirmar árvore. Aplicar xmqr-tests.
Objetivo: baseline reproduzível de RSS/CPU com1,8,32 conexões ociosas e
latência de confirmação durávelQoS1 em loopback open-lab. Três repetições,
warmup explícito, payload256, publicação sequencial; sem throughput máximo.
Escopo: scripts/benchmark_baseline.py, docs/performance-baseline.md, JSON de
resultados resumidos e registroP62. Sem alteração runtime/client/quotas/versão.
Harness próprio independente da CLI evita custo de subprocesso por mensagem.
Registrar hardware/WSL/toolchain/binárioSHA/sourceHEAD, parâmetros, RSS amostrado,
HWM do processo e CPU por delta /proc/stat. p50/p95/p99, média e variabilidade.
ACK não significa consumo da aplicação. Estado/processos só temporários /tmp;
timeout e cleanup, DISCONNECT e SIGTERM limitados. Recusar plataforma/args inválidos.
Aceite: cenário real, JSON legível, contagens e ACKs específicos, shutdown0,
nenhuma conclusão de RAM por cliente/capacidade máxima/produção/TLS/fan-out.
Falhas: revisar prompt antes de corrigir. Gates Python/proporcionais; Rust
não repetido por ferramenta/documentação externa. Commit/push autorizados;
sem tag/release por baseline inicial. MQTT5/WS/bridge e demais cenários futuros.

## rev2 — refinamento após ensaio inicial

Primeiro ensaioPASS, mas200 mensagens produziram janelas de19–25ms e /tmp é
tmpfs. Não publicar esse resultado como medição de disco/CPU robusta.
Acrescentar --state-root, registrar filesystem; usar diretórios temporários
no /home nativo,2000 mensagens e100warmup. QoS1retained com sequência no payload
para modificar estado em cada publicação. Comparar antes/depois hashes do
binário e arquivosRust/manifests. Sem alteração no broker ou promessa física.

## rev3 — timestamp do relatório

O campo started_utc foi preenchido no fim; renomear para completed_utc no
harness e na cópia documental dos resultados, preservando os números medidos
e o JSON original emtarget. Esta é correção de metadado, não nova medição.
Registrar hash do harness usado na medição antes desta correção.
