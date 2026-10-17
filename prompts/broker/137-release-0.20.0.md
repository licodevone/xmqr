# P137 rev1 — prerelease experimental broker 0.20.0

Entrada: `main` após P136, broker publicado 0.19.0, documento durável v8; fases 6A–6D abertas. Exigir CI verde de P136/C73 antes do bump.

Objetivo: publicar checkpoint 0.20.0 com P134 Receive Maximum e P136 Maximum Packet Size MQTT 5. Bump Cargo/lock, Dockerfile, changelog, VERSIONING, README/plano e nota de release. O `mqtt-admin` legado acompanha; `xmqr-admin` independente permanece 0.4.0. Não há migração do documento v8.

Aceite: gates da fonte exata, integração P134/P136 e CI PASS; pacote Ubuntu26 amd64 e imagens Docker numeradas com versão/revisão inspecionadas, sem instalar no WSL do operador; tag anotada imutável `v0.20.0`, prerelease GitHub com `.deb`, imagens, SHA-256 e manifesto conferidos; Docker Hub numerado com digest remoto, `latest` intacta. Rollback de v8 para broker 0.19.0 não exige migração reversa, mas backup privado segue obrigatório antes de upgrade. Não declarar fase 6 completa.
