# P72 rev1 — capacidade QoS/fan-out/mTLS

Data: 2026-10-12. Entrada: broker HEAD b47e063, 0.11.2; client 0.7.1.
Fase 1 aceita; baseline P62 disponível. Checklist P71 e arquivos locais preservados.

Objetivo: harness Linux independente da CLI para comparar QoS0/1/2 e entrega
a 1/8 assinantes, em open-lab e secure-mtls, sem alterar quotas ou runtime.

Escopo: scripts/benchmark_fanout.py, validação do harness, relatório JSON público
sem segredos, docs/performance-fanout.md, evolution-plan.md e registro P72.
Reusar amostragem P62 e fixtures wire/certificados. Credencial exclusivamente
de teste, gerada em diretório temporário, nunca obtida da instalação existente.

Método: publicação sequencial, payload com sequência verificável, warmup,
3 repetições; confirmar recepção em todos os assinantes e completar ACKs QoS1/2
nas duas direções. Medir entrega wire completa (incluindo ACKs), não negócio.
Registrar RSS/CPU, p50/p95/p99, taxa, ambiente, hashes do binário/harness e fonte.
Contagens e payloads obrigatórios; report não sobrescrito. SIGTERM/shutdown0;
timeouts, limite total de cenário e limpeza de recursos próprios mesmo em falha.

Aceite: matriz real 2 transportes × 3 QoS × 2 fan-outs × 3 repetições; metadados
reproduzíveis, negativos de argumentos e CA/senha, sem conclusões de throughput
máximo/produção. TLS exige CA/SAN verificados e certificado+senha+ACL.
Registros PASS/FAIL/BLOCKED separados; revisar prompt antes de corrigir falha.

Validação proporcional: sintaxe Python, negativos, smoke e campanha WSL Ubuntu26.
Sem alteração Rust; binário atual confirmado por --version e SHA-256.
Sem mudança de versão/tag vX.Y.Z apenas por benchmark. Commit/push autorizados
pelo pedido; tag de versão fica para marco funcional validado. Compatibilidade
e migração: nenhuma. Fase 2 fica aberta para saturação/filas/ESP32.

## rev2 — ambiente do gate documental

Campanha e contratos PASS. Verificação suplementar de inventário não executou
Cargo por PATH ausente no shell WSL sem perfil. Não alterar dependências ou
inventário para contornar ambiente; repetir com /home/licod26/.cargo/bin no PATH
e registrar tentativa/resultado. Links locais e diff-check já passaram.
