# P54 rev1 — primeira fatia dos limites configuráveis

Entrada: main d95fcb7; alteração local AGENTS.md pertence ao usuário e será
preservada, fora do commit. Aplicar skill xmqr-rust-mqtt.
Objetivo: tornar configurável a admissão de conexões TCP, primeira fatia da
fase1. TOML [limits].max_connections e MQTT_MAX_CONNECTIONS explícito prevalece.
Default do executável64, faixa1..64; não ampliar capacidade sem benchmark.
Não confundir conexões simultâneas com sessões persistentes ou mensagens/s.
Sem alterar quotas duráveis, formato de estado, codec, TLS, ACL ou client.
Uma redução de conexões não elimina sessões; aplicar no próximo restart.
Escopo: configuration.rs, main.rs, testes unitários/processo, documentação e
registro P54. Cliente real exercita recusa TCP sem prometer diagnóstico MQTT5.
Aceite: default/precedência/tipos/zero/acima64/não Unicode, recusa antes do estado;
limite1 recusa segunda conexão e libera vaga após desconexão. fmt/test/clippy/
build e integração C27. Revisar prompt antes de corrigir falha encontrada.
Sem instalar nem alterar serviços reais. Commit/push autorizados; não anunciar
fase1 completa nem criar release antes de todas as quotas/pacotes validados.
