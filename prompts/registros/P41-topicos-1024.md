
# P41 — Resultado real da alteração de limite

Estado: implementado; validação Unix/recuperação ainda pendente. Prompt P41
preparado antes de editar. Constante pública mqtt::MAX_TOPIC_BYTES = 1024 usada
pelo broker e CLI. UTF-8 contado em bytes, sem normalização. Quotas de sessões,
assinaturas, pacote, payload, senha, filas e documento preservadas; formato v1.
Rollback para snapshot 256 exige backup compatível anterior se houver nomes longos.

## Execução em Windows — Rust 1.98.1

| Check | Resultado real |
| --- | --- |
| fmt --all -- --check | PASS |
| cargo test --locked --offline | 25 PASS / 17 FAIL: fsync de diretório exige Unix |
| cargo test --locked --offline --bins | mqtt-admin: 3 FAIL por requisito Linux/WSL; demais executados separadamente |
| cargo test --locked --offline --bin mqtt-client | 11 PASS |
| cargo test --locked --offline --bin mqtt-broker | 4 PASS |
| Clippy --all-targets -D warnings | FAIL: dois avisos Windows preexistentes em users.rs/credentials.rs, intactos |
| Clippy --lib -D warnings | PASS |
| inventário de licenças com python -X utf8 | PASS |
| git diff --check | PASS |

Testes novos de tipo, wire PUBLISH/SUBSCRIBE/UNSUBSCRIBE, CLI e ACL passaram
para 1024/1025 bytes e UTF-8 multibyte. O novo teste de roteamento/retained/offline
restore compilou, mas falhou ao preparar Store, antes das asserções: suporte Unix
necessário. Não conta como teste de recuperação aprovado.

Falha anterior de início rustc (0xc0e90002) não reproduzida nesta retomada;
compilação nativa concluída. Não se determinou a causa do erro inicial.
Inventário inicialmente encontrou encoding cp1252; -X utf8 resolveu sem editar script.

WSL Ubuntu-24.04 e Ubuntu-26.04 não têm cargo/rustc/Mosquitto encontrados nos
diretórios usuais. Gates Unix e interop externa estão BLOCKED; nada foi instalado.
Não corrigidos suporte Windows ou warnings alheios ao pedido. Próximo passo mínimo:
executar a mesma revisão em ambiente Rust Linux/WSL existente e preparado, passando
fmt/test/clippy e interop; preparação/instalação de ambiente requer pedido separado.

Originais/copias e prompts de clientes preservados; sem commit/push/deploy.
Resultados e escopo detalhados em [VALIDACAO-P41.json](../VALIDACAO-P41.json).


## Retomada Unix - 2026-10-07

Mesma copia /mnt/d/projects/my-project/xmqr, Ubuntu-26.04, Rust 1.99.0.
Artefatos Cargo isolados no workspace; estado de teste temporario.

| Gate | Resultado |
| --- | --- |
| cargo test --locked --offline | PASS, exit 0 |
| cargo fmt --all -- --check | PASS, exit 0 |
| cargo clippy --locked --all-targets --offline -- -D warnings | FAIL, exit 101 |
| python3 scripts/license_inventory.py --check | PASS, exit 0 |
| cargo build --locked --offline --bins | PASS, exit 0 |

Suíte: 74 testes aprovados; contagens por alvo [53, 4, 4, 13, 0].
Teste P41 long_utf8_topics_route_and_survive_retained_offline_restore:
PASS; recupera filtro, fila offline e retained com nomes UTF-8 de 1024 bytes.
Cliente proprio mqtt-client/rumqttc: seis cenarios PASS (pub/sub QoS 0/1/2
com topico UTF-8 de 1024 bytes; retained 1024 bytes apos reinicio; rejeicao
CLI pub/sub com 1025 bytes). Evidencia limitada a open-lab, sem TLS/ACL externa.

Clippy 1.99 local e CI remoto run37393863354: clippy::assert_is_empty em
src/mqtt/store.rs:296, debug_assert!(remainder.is_empty()). Arquivo intacto
por P41; linha presente em HEAD. Falha preexistente, nao corrigida neste escopo.
No CI remoto fmt/test passaram; inventario/build/interop foram pulados.
Resultados locais atuais nao alteram o status remoto nem validam outro commit.

Interop especifica Mosquitto: NOT_RUN; usuario solicitou nao instalar.
Cliente proprio nao substitui evidencia de compatibilidade com Mosquitto.
Nenhum gate global de release aprovado: Clippy pendente e interop externa nao rodada.
Versao 0.5.0 continua em desenvolvimento, sem tag/release publicada.
Sem alteracoes funcionais adicionais, instalacao Rust/Mosquitto, commit/push/tag/release.
A primeira tentativa offline faltava cache argon2; inventario cargo metadata
preencheu dependencias existentes do lock via rede; gates subsequentes offline.
