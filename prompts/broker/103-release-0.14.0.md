# P103 rev1 — publicação experimental do software da fase 4

2026-10-15. Entrada: tag/release broker0.13.1 e client0.11.1 publicados;
P100/B11 e P101/B09 passaram integração externa e gates Rust Ubuntu26.
P102/E02 foi gravado na COM4, mas parou na associação Wi-Fi: o SSID privado
da campanha E01 está invisível na varredura atual; nenhuma rotação física foi
executada. O mantenedor foi avisado e a rede foi solicitada de volta.

Objetivo: publicar broker/legado admin0.14.0 como prerelease da fatia de
software B09/B11, sem anunciar fase 4 completa nem E02 aceita. Atualizar
Cargo.toml/lock, Dockerfile e documentação coerentemente. Tag imutável no
commit exato após fmt/test/Clippy/build, integração mTLS/TLS-senha, inventário,
notices, pacote/Docker e hashes. Gerar .deb/arquivos/checksums, verificar
assets remotos e imagem numerada no Docker Hub; não mover `latest`. Client e
admin independente não mudaram e conservam versões anteriores.

Registrar limites: políticas distintas apenas estáticas por endpoint mTLS;
TLS e rotação compartilhados; TOML restart-only; CRL/conexões existentes;
E02 físico pendente por Wi-Fi externo. Não reescrever tags anteriores.

## rev2 — C05 concluído em repositório independente

C50/C05 passou unidades e integração real mTLS/TLS-senha após P103 ser criado.
O client terá a release independente 0.12.0/C51; a fase 4 global continua
aberta somente por E02 físico. Não misturar binários ou tags dos repositórios.
