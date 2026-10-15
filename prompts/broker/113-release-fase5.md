# P113 rev1 — release experimental do broker fase 5

2026-10-15. Entrada 0.14.0, release v0.14.0 imutável; P107–P112 implementam canal administrativo, auditoria e diagnóstico. A fase 5 tem escopo finito da matriz A02/A03/A04/A05/A07/A08/A09/B13/B14 e client C03/C04/C06/C08.

Após gates e aceite registrados, elevar broker/mqtt-admin legado para 0.15.0. Atualizar lock, documentação e notas. Criar commit limpo, testar binários desse commit, tag anotada v0.15.0 e prerelease GitHub sem mover tags antigas/latest. Empacotar deb Ubuntu26amd64 e imagens numeradas com hashes se gates locais de distribuição passarem. Não anunciar produção nem conformidade MQTT total. Registrar SHA, assets e limitações reais.
