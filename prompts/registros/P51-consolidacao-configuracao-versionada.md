# P51 rev1 — execução 2026-10-11

Entrega: desenho de configuração TOML versionada, precedência/defaults,
segurança, caminhos, compatibilidade e aceite futuro. Roadmap com checkpoint
0.10.0 atual e etapas históricas identificadas; matriz atual contextualizada.
Parser/limites novos NOT_IMPLEMENTED nesta fatia, sem anúncio de recurso pronto.

Ubuntu26.04/WSL2, mesma fonte do repositório: fmt --check PASS; cargo test
--locked PASS (74 lib +4 admin +4 main +1 backup =83); clippy --locked
--all-targets -- -D warnings PASS; build --locked --bins PASS.
Integração C27 com cliente C35: quatro testes em três rodadas PASS; shutdown3
PASS; LastWill9 PASS. Processos/estado temporários, não o serviço instalado.

Inventário de licenças PASS com Python -X utf8; tentativa anterior sem UTF8 no
Windows falhou por cp1252, sem editar script. Links, exemplo TOML, bash -n e
diff --check PASS. TLS externos/Mosquitto adicionais e benchmark NOT_RUN;
recepção de telemetria ESP32 real NOT_RUN. Não afirmar suporte MQTT5/produção.

Sem alteração de versão, tag, estado MQTT, secrets, serviços ou firmware.
Commit/sincronização autorizados anteriormente na conversa.
