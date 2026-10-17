# P145 rev1 — prerelease experimental broker 0.23.0

Entrada: P144 `376ad4d764974e31e184db2df0efaeb079666d45` com [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39001551013); C80 aceito e C81 aguardando CI. Este prompt precede a alteração de versão. Exigir CI verde de C81 antes do bump conjunto.

Objetivo: publicar checkpoint broker 0.23.0 e `mqtt-admin` legado com Receive Maximum inbound no CONNACK MQTT 5 quando cabe, preservando Maximum Packet Size e Topic Alias. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release. Documento durável continua v10; rollback ao broker 0.22.0 não exige downgrade de formato, mas requer backup e ensaio real de ciclo. `xmqr-admin` independente permanece 0.4.0. Não marcar fase 6C global como concluída.

Aceite: gates locais e CI da fonte exata PASS; pacote Ubuntu26 amd64, imagens numeradas broker/admin, ciclo install/upgrade/downgrade/remove em container descartável, tag anotada imutável `v0.23.0`, prerelease GitHub com manifesto/checksums conferidos, Docker Hub numerado com digest remoto, `latest` intacta. Sem modificar a instalação WSL do operador nem executar ensaio físico ESP32.
