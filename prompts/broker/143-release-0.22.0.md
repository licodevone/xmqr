# P143 rev1 — prerelease experimental broker 0.22.0

Entrada: P141/P142 entregam metadados de PUBLISH MQTT 5 em `main`; broker publicado 0.21.0. Exigir CI verde de P142 e C78 antes do bump. Este prompt precede qualquer alteração de versão.

Objetivo: publicar checkpoint 0.22.0 do broker e `mqtt-admin` legado com Payload Format Indicator, Content Type, Response Topic, Correlation Data e User Property. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release. O `xmqr-admin` independente permanece 0.4.0. O documento durável passa a v10; rollback ao broker 0.21.0 exige backup privado v8 anterior à primeira gravação P141/P142. Não alegar suporte MQTT 5 integral nem homologação do `mosquitto_sub` 2.0.22 para alias abreviado.

Aceite: gates locais e CIs da fonte exata PASS; pacote Ubuntu26 amd64, imagens numeradas broker/admin inspecionadas, ciclo upgrade/downgrade/remove em contêiner descartável sem tocar instalação WSL do operador; tag anotada imutável `v0.22.0`, prerelease GitHub com manifesto/SHA-256 dos anexos conferidos, Docker Hub numerado com digest remoto, `latest` intacta. Checklist somente após evidência. Fases 6A–6D e 7–9 permanecem abertas; sem ensaio físico ESP32.
