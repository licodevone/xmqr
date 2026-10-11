# P58 — teto uniforme de pacote MQTT completo

ID/versão: P58 rev1, 2026-10-11. Pedido autorizado: finalizar fase1; implementação desta fatia e documentação, sem avanço de fase.

Estado de entrada: broker HEAD57d23c0d3008ad869f81b89abe243c3e9790ee85, árvore inicialmente limpa, mqtt-broker0.10.0/Rust2024/MSRV1.88; client independente HEAD6ee5aa8 usa teto completo65536. P55 com aceite Unix pendente; Windows não substitui fsync Unix. Skills xmqr-rust-mqtt e xmqr-tests lidas, contratos preservados.

Objetivo: broker e client recusam pacotes cuja soma do primeiro byte, bytes reais de Remaining Length e corpo excede65536 bytes. Broker hoje limita apenas Remaining Length, permitindo4 bytes extras na borda.

Escopo: src/mqtt/codec.rs, testes unitários wire independentes, docs/conformance/mqtt311-status.md, docs/architecture/configuration.md, README.md, CHANGELOG.md e registro P58. Client C38 e integração sob agente responsável; plano e pacote sob coordenação. Não editar durabilidade, quotas lógicas, TLS/SAN, ACL, QoS, versões ou releases nesta fatia.

Requisitos: rejeitar N+1 tão logo cabeçalho completo indique excesso, antes de aguardar corpo; aceitar N respeitando validações de tipo/campos; contar bytes reais também em Remaining Length não mínimo; preservar fragmentação e concatenação sem aplicar teto ao agregado de vários frames. Payload permanece4096 e tópico/filtro1024 UTF-8. Encoder verifica pacote completo.

Fonte normativa confirmada: OASIS MQTT3.1.1 §2.2.3 (Remaining Length exclui seus próprios bytes, além do primeiro byte), §3.1.3.5 senha binária e §3.3 PUBLISH. Teto65536 e payload4096 são quotas locais, não limite normativo MQTT. https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html

Compatibilidade/migração: WAL/snapshot/documento preservados, sem migração. Frames de65537..65540 anteriormente aceitos no framing serão recusados; retry deve reduzir/particionar operações respeitando quotas. Configuração de limites permanece restart-only; pacote/payload não recebem novos knobs.

Aceite: negativos cabeçalho N/N+1, frames completos válidos independentes em N/N+1, fragmentação/concatenação, Remaining Length com bytes reais e payload4096/4097 em QoS0/1/2 e Will; fmt, testes portáveis codec, Clippy/build. cargo test global Unix e integração cross C38 exigem ambiente Unix real. Registre BLOCKED quando ausente, sem afrouxar fsync ou declarar fase1 encerrada.

Evidência: prompts/registros/P58-pacote-completo.md com comandos/códigos reais; falhas exigem revisão deste prompt antes de correção. Tags/commit/push coordenados pelo agente principal somente com gates de aceite completos.
