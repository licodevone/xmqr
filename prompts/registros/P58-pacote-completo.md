# Execução P58 — pacote completo

Data:2026-10-11. Prompt58-pacote-completo.md rev1 criado/apresentado antes do código.
Base broker57d23c0d3008ad869f81b89abe243c3e9790ee85, árvore inicialmente limpa.
Windows x86_64; rustc1.98.1 (48a229cea,2026-09-01) e cargo1.98.1
(797e8a9bc,2026-08-05). Rust2024/MSRV1.88 declarados no manifest.

Mudança: frame_header conta primeiro byte e número real dos bytes Remaining
Length no teto65536; encoder PUBLISH confere cabeçalho+corpo. Buffer parcial
limita65536 antes de novas leituras (chunks já lidos podem conter frames
concatenados, consumidos individualmente). Nenhuma mudança em WAL/snapshot,
quotas duráveis, TLS/SAN/ACL/QoS, versão ou dependências.

Fonte confirmada online: OASIS MQTT3.1.1 §2.2.3 e §3.1.3.5:
https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html
Teto é quota local; norma não impõe65536 ou4096.

| Comando/cenário | Código/status | Resultado |
| --- | --- | --- |
| git status --short (safe.directory repo) inicial |0 PASS | árvore limpa |
| git diff --check |0 PASS | sem whitespace inválido |
| cargo fmt --all |0 PASS | formato aplicado |
| cargo fmt --all -- --check |0 PASS | formato válido |
| cargo test --locked mqtt::codec::tests |0 PASS |12 testes codec;55 lib filtrados; demais targets filtrados |
| cargo clippy --locked --all-targets -- -D warnings |0 PASS | sem lint |
| cargo build --locked --bins |0 PASS | broker/admin debug; linker MSVC emite informativo de criação de .lib/.exp |
| Integração broker/client e recuperação Unix |BLOCKED | Windows sem WSL disponível; não houve runtime durável neste escopo |

Vetores independentes N/N+1: CONNECT binário com65514/65515 bytes de senha
produz65536/65537 bytes totais, payload MQTT de aplicação não usado para
forçar pacote. Aceito decodifica sob fragmentação e com PING concatenado;
rejeitado falha inclusive apenas com4 bytes de cabeçalho sem corpo. Outros
vetores cobrem Remaining Length65536 (65540 total),4 dígitos não mínimos
contados pelo tamanho real, PUBLISH4096/4097 nos3 QoS e Will4096/4097.

Documentação: README, CHANGELOG, configuração e matriz3.1.1. Client C38 e
gate Unix sob agentes responsáveis. Sem commit/tag/release por este agente;
aceite fase1 e publicação dependem gates globais, integração e pacote Unix.
