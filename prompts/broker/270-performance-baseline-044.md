# P270 v1.0 — medir e priorizar desempenho do Broker 0.44.0

## Entrada

Broker candidato 0.44.0 no commit
`02097af27efe601ada936dc964d82936e6771e5a`. Teto de 64 conexões e
64 sessões por instância, estado v16. Os resultados P62, P72 e P80
pertencem às fontes 0.11.x. A publicação da 0.44.0 segue os gates do P269.

## Objetivo e escopo

Estabelecer uma referência reproduzível de um nó em Ubuntu para conexões
ociosas, admissão sob rajada e entrega de mensagens. Reutilizar
`scripts/benchmark_baseline.py`, `scripts/benchmark_pressure.py` e
`scripts/benchmark_fanout.py`. Guardar relatórios em `target/` e resultados
sanitizados em `prompts/registros/P270-performance-baseline-044.md`.
O checkpoint usa os limites e o formato existentes. Alterações de runtime
e migrações têm prompts e testes de aceitação próprios.

## Execução em laboratório Ubuntu

Em checkout isolado do commit de entrada, use Ubuntu 26.04, Rust 1.99.0,
Python 3.11+, OpenSSL e filesystem nativo. Os scripts de mTLS usam o `mqtt-admin`
compilado junto com o broker e as fixtures de certificado de um checkout
vizinho `../xmqr-client`. Fixe esse checkout em
`9e1d011ffa22aa1225d3775b6fc99a06ae6dfc60`. Certificados, diretórios e
listeners pertencem ao laboratório.

```sh
(
set -eu
test "$(git rev-parse HEAD)" = 02097af27efe601ada936dc964d82936e6771e5a
test "$(git -C ../xmqr-client rev-parse HEAD)" = 9e1d011ffa22aa1225d3775b6fc99a06ae6dfc60
cargo +1.99.0 build --locked --release --bins --target-dir target
mkdir -p target/p270-state
sha256sum ../xmqr-client/validation/C27-integration.py
python3 -B scripts/test_benchmark_fanout.py
python3 -B scripts/test_benchmark_pressure.py
python3 -B scripts/benchmark_baseline.py --broker target/release/mqtt-broker \
  --state-root target/p270-state --idle-seconds 30 --report target/p270-idle.json
python3 -B scripts/benchmark_pressure.py --broker target/release/mqtt-broker \
  --admin target/release/mqtt-admin --state-root target/p270-state \
  --limits 1 8 32 64 --report target/p270-pressure.json
python3 -B scripts/benchmark_fanout.py --broker target/release/mqtt-broker \
  --admin target/release/mqtt-admin --state-root target/p270-state \
  --report target/p270-fanout.json
)
```

Execute em ordem e interrompa a campanha se qualquer comando falhar. Use
nomes novos para repetições. Registre revisão, binários, hashes dos scripts
e da fixture, CPU, RAM, filesystem e parâmetros usados.

## Aceite e ordem de evolução

- Comparar três repetições por cenário. Para conexões, registrar aceitas,
  recusadas, latência p50/p95/p99 e tempo de recuperação da rajada. Para
  mensagens, separar publicações, entregas, latência até o assinante,
  duplicatas, CPU, RAM e pressão das filas. QoS 1 e 2 exigem verificação
  dos handshakes aplicáveis, além de checagem de entrega.
- Tratar os resultados existentes como linha de base. P62 mede carga
  sequencial, P72 mede entregas sequenciais com fan-out e P80 mede pressão
  e rajadas. Uma campanha posterior de carga mista deve usar vários
  publicadores ativos e reconexões simultâneas, com tráfego e janelas fixos.
- Correlacionar gargalos com duração de commit e fila do roteador. Quando
  necessário, separar TLS e autenticação por métricas adicionais. Se
  persistência dominar, avaliar WAL incremental e agrupamento de commits
  com prazo curto. Preservar a confirmação MQTT após a barreira durável
  aplicável, inclusive em crash/replay. Se matching dominar, avaliar
  índice de tópicos preservando ACL, wildcards e assinaturas compartilhadas.
- Validar 256 e 1.000 conexões em etapas posteriores. Revisar em conjunto
  quota de sessões, orçamento de filas e limite do documento persistido.
  Aceitar um patamar somente com capacidade repetível, sem regressão
  de correção, recuperação ou segurança. Cluster fica em etapa própria.
