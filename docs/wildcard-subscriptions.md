# Filtros MQTT 3.1.1 — série 0.5 em desenvolvimento

`+` ocupa exatamente um nível; `#` ocupa o último nível e aceita zero ou
mais níveis. Níveis vazios, Unicode e maiúsculas/minúsculas são preservados.
Não há normalização ou criação prévia de tópico.

| Filtro | Publicação | Resultado |
| --- | --- | --- |
| `sensores/+/temperatura` | `sensores/sala/temperatura` | recebe |
| `sensores/+` | `sensores/` | recebe o nível vazio |
| `sensores/+` | `sensores` | não recebe |
| `sensores/#` | `sensores` | recebe |
| `#` | `$SYS/status` | não recebe |
| `$SYS/#` | `$SYS/status` | recebe |

Filtros como `sensores+`, `a/#/b` e `a/+extra` são inválidos. PUBLISH nunca
aceita `+` ou `#` no nome. Pacotes malformados encerram a conexão; falta de
permissão de assinatura produz SUBACK `0x80`.

## Laboratório

Com o broker `open-lab` rodando em loopback, use o cliente já compilado:

```bash
"${CARGO_TARGET_DIR:-target}/debug/mqtt-client" sub --open-lab \
  --topic 'sensores/+/temperatura' --qos 1 --client-id exemplo-sub
"${CARGO_TARGET_DIR:-target}/debug/mqtt-client" pub --open-lab \
  --topic 'sensores/sala/temperatura' --message '24' --qos 1 --client-id exemplo-pub
```

Execute sub e pub em terminais separados. Os binários continuam chamados
`mqtt-client` e `mqtt-broker` durante a série 0.x. Os modos sem TLS permanecem
limitados a loopback.

## ACL, entrega e limites

`publish` concede nomes concretos; `subscribe` concede literalmente o filtro
solicitado. Uma concessão `sensores/+` não autoriza `sensores/#`. Na entrega,
o tópico concreto também deve casar com uma concessão. Filtros iniciados por
coringa não incluem a raiz `$`; para ela é preciso uma concessão explícita.

Cada cliente recebe uma publicação por mensagem, no menor QoS entre o da
publicação e o maior QoS das assinaturas que casam. Retained é deduplicado
entre filtros do mesmo SUBSCRIBE. UNSUBSCRIBE remove somente a assinatura
textualmente idêntica. Sessões persistentes mantêm filtros e fila offline;
na inicialização, ACLs removidas purgam assinaturas e entregas não autorizadas.

O matcher é iterativo e não aloca; o trabalho total é limitado por 64 sessões,
256 assinaturas por sessão e 1024 bytes UTF-8 por tópico/filtro. O armazenamento
mantém os limites anteriores de 64 mensagens offline e 32 inflight por sessão.
Uma transição que exceda quota não é parcialmente confirmada. Esses limites
são fixos nesta fatia; não há promessa de capacidade ou latência sob carga.

## Validação reproduzível

```bash
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked --bins
python3 scripts/license_inventory.py --check
python3 scripts/verify_interop.py --broker "${CARGO_TARGET_DIR:-target}/debug/mqtt-broker"
```

O roteiro requer Python 3.11+, `mosquitto-clients` e `stdbuf` (coreutils),
disponíveis no Ubuntu de validação. Usa diretórios temporários próprios,
portas loopback descobertas, IDs explícitos e encerramento somente dos
processos criados pelo teste. Não conecta a instâncias existentes.

Evidência local em 2026-10-05: Ubuntu 24.04 WSL2, Rust 1.98.1,
Mosquitto/libmosquitto 2.0.18. A base 0.4 passou em 58 testes internos antes
da alteração. A fatia adiciona vetores normativos, propriedades geradas com
referência recursiva independente, profundidade máxima, sobreposição, quotas,
ACL e recuperação. Quatro cenários externos cobrem QoS 0/1/2, sobreposição,
retained e namespace `$`, reinício, fila offline, UNSUBSCRIBE e filtros inválidos.

Os testes externos dessa fatia usam `open-lab`; não provam interoperabilidade
com TLS/mTLS e ACL, nem perda real de energia, alta escala ou conformidade
MQTT completa. Last Will continua rejeitado. Client IDs vazios não fazem
parte dos vetores de sucesso: o comportamento de recusa exige uma fatia própria.

## Atualização e retorno

Pare a instância e faça backup completo do diretório de estado antes de
atualizar. WAL e documento MQTT continuam na versão 1; a 0.5 lê estados 0.4.
Para retornar à 0.4, remova todas as assinaturas wildcard com UNSUBSCRIBE
antes da parada ou restaure um backup completo anterior em outro diretório.
Não reverta apenas parte do WAL/snapshot.

Use GitHub para sincronizar as cópias Windows e WSL: envie os commits da
cópia de trabalho; na outra, confirme `git status` limpo e execute
`git pull --ff-only`. Clonar ou abrir a pasta não sincroniza alterações locais.

Fontes normativas: [OASIS MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html),
§§3.3.5, 3.8.4, 3.10.4 e 4.7. Decisão:
[ADR 0002](architecture/adr-0002-topic-filters.md).


## Compatibilidade do limite de 1024 bytes

P41 amplia a quota local de tópico/filtro para 1024 bytes UTF-8; não normaliza
Unicode e não altera número de sessões/assinaturas, payload, pacote ou quotas
do documento. O matcher continua linear, com até quatro vezes o orçamento de
bytes por filtro; não há promessa nova de capacidade/latência sob carga.
WAL e documento MQTT continuam v1: estado anterior é legível no novo código.
O snapshot anterior de 256 bytes não restaura nomes/filtros longos. Antes de
gravar nomes >256 bytes, preserve backup completo com o broker parado. Para
voltar ao snapshot anterior, use backup compatível anterior em outro diretório;
remover somente subscriptions não basta se retained/offline/inflight ainda
contiverem nomes longos. Não misturar WAL e snapshot de momentos diferentes.
