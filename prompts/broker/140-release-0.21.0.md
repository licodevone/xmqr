# P140 rev1 — prerelease experimental broker 0.21.0

Entrada: P138 e P139 entregam Topic Alias MQTT 5 de entrada e saída em `main`; broker publicado 0.20.0; fases 6A–6D abertas. Exigir CI verde da fonte P139 e C75 antes do bump. Este prompt precede qualquer alteração de versão.

Objetivo: publicar checkpoint 0.21.0 do broker e `mqtt-admin` legado, com Topic Alias limitado por conexão. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release. O `xmqr-admin` independente permanece 0.4.0. O documento durável continua v8. Descrever explicitamente a incompatibilidade observada do `mosquitto_sub` 2.0.22 com a forma abreviada, reproduzida sem XMQR; não alegar interoperabilidade nessa direção ou conformidade MQTT 5 integral.

Aceite: gates locais da fonte exata, integração P138/P139/C75 e CI PASS; pacote Ubuntu26 amd64, imagens numeradas broker/admin inspecionadas, ciclo upgrade/downgrade/remove em contêiner descartável sem tocar o WSL do operador; tag anotada imutável `v0.21.0`, prerelease GitHub com manifesto e SHA-256 de cada anexo conferidos, Docker Hub numerado com digest remoto, `latest` intacta. Registrar rollback v8 e fases ainda abertas. Se qualquer gate falhar, manter checklist e release pendentes até correção.
