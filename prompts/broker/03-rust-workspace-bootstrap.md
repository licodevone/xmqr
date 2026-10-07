> **Adaptação XMQR — 2026-10-07.** Histórico de escopo da origem, sem prova de execução no XMQR. Não reaplicar sobre o código existente. Para validar o snapshot atual, usar broker/36 e clients/24.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/03-rust-workspace-bootstrap.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — bootstrap do workspace Rust

Crie um workspace Rust mínimo que compile e sustente fatias verticais. Proponha crates somente quando houver fronteira concreta; uma base razoável é codec/protocol, core/domain, server/runtime, persistence e test-support, mas adapte ao contexto.

Inclua: pin de toolchain quando decidido, formatação, lint estrito, testes, feature flags por versão MQTT, tratamento de erro, logging estruturado e binário que inicia, valida configuração e encerra graciosamente. Não implemente features falsas nem traits vazias.

Valide com build, clippy, tests e execução curta do binário. Registre comandos de desenvolvimento e uma primeira decisão arquitetural.
