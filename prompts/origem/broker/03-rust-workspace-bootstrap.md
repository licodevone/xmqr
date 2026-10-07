# Prompt — bootstrap do workspace Rust

Crie um workspace Rust mínimo que compile e sustente fatias verticais. Proponha crates somente quando houver fronteira concreta; uma base razoável é codec/protocol, core/domain, server/runtime, persistence e test-support, mas adapte ao contexto.

Inclua: pin de toolchain quando decidido, formatação, lint estrito, testes, feature flags por versão MQTT, tratamento de erro, logging estruturado e binário que inicia, valida configuração e encerra graciosamente. Não implemente features falsas nem traits vazias.

Valide com build, clippy, tests e execução curta do binário. Registre comandos de desenvolvimento e uma primeira decisão arquitetural.

