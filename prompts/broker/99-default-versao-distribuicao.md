# P99 rev1 — corrigir default da imagem após P97

2026-10-15. Entrada `4d26cc31cf23efc1e7032cdcc156d7cf3b9a9749`,
tag `v0.13.0` já enviada, árvore limpa. `scripts/test_distribution.py`
falhou: Cargo 0.13.0 e `ARG VERSION=0.12.0` divergem. Nenhuma release0.13.0
será publicada. O pedido autoriza completar a distribuição da fase 4.

Objetivo: corrigir o default Docker e emitir versão patch0.13.1 em novo commit
e tag, preservando a tag0.13.0 imutável. Escopo: Cargo.toml/lock, Dockerfile,
CHANGELOG/VERSIONING/registro, validação e artefatos. Não alterar TLS/MQTT.

Aceite: testes de distribuição, gates Rust, integração P97/C48 e build Docker
sem `--build-arg VERSION` com `--version` correto. Publicar apenas release
0.13.1 após checksums e imagem de commit exato; 0.13.0 permanece tag de código
sem release, documentada como substituída antes da distribuição.
