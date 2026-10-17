# P157 rev1 — marco broker 0.27.0 e documento v14

Entrada: broker 0.26.0 publicado com grupos compartilhados persistentes v13; P156 introduz proveniência/redistribuição QoS1 em v14 e precisa CI do commit funcional. Este prompt precede a atualização de versão.

Objetivo: preparar broker e `mqtt-admin` legado 0.27.0 com fonte P156 validada. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING e nota de release. Documentar rollback: 0.26.0 e admin independente 0.8.0 não reabrem v14; backup privado v13 anterior à primeira gravação é obrigatório. Client 0.24.0 continua parceiro; não bumpá-lo sem mudança própria. Atualizar admin independente para core v14 em A18 antes da publicação do broker.

Aceite: commit exato com testes Rust, fmt, Clippy, build release, licenças, contratos de pacote e CI; pacote Ubuntu 26.04 amd64; imagens broker/admin legado numeradas; ciclo descartável de upgrade/rollback com client existente e estado privado preservado; admin A18 backup/restore v14; tag anotada, prerelease, anexos e digests remotos verificados. Sem mover `latest`, instalar no WSL do operador ou marcar fase 6D completa.
