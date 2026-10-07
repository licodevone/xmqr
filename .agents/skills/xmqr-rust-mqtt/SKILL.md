---
name: xmqr-rust-mqtt
description: "Implementar ou corrigir Rust e MQTT no XMQR quando houver pedido de mudança funcional, preservando protocolo, segurança e persistência existentes."
---

# Implementação Rust/MQTT no XMQR

Leia [AGENTS](../../../AGENTS.md), [contrato](../../../prompts/contrato-base.md)
e [modelo de alteração](../../../prompts/broker/18-feature-iteration.md).
Prepare o prompt da fatia antes de editar, mantendo o escopo já autorizado.

Trace o caminho real: transport/mod.rs -> mqtt/mod.rs -> codec/router/store;
auth/mod.rs governa principal/ACL; persistence/actor.rs separa disco dos workers.
CLI mqtt-client usa rumqttc; mqtt-admin/users.rs é fluxo administrativo Unix.
Não recriar funcionalidades pelos prompts históricos, nem copiar o consumidor.

Para a fatia, declare estados/transições, comportamento no wire, limites em bytes,
requisitos OASIS confirmados, ownership e falhas. Alterações que cruzem QoS,
retained e sessão devem explicitar commit antes de ACK, geração no takeover,
packet identifiers e rollback do documento v1. Preserve ACL no restore/replay.
Quotas excedidas e persistência incerta não podem confirmar estado inexistente.

Confira constants do snapshot e a [cobertura](../../../prompts/COBERTURA.md),
especialmente o limite compartilhado de 1024 bytes UTF-8 do broker/CLI (P41). Não ampliar outras quotas sem decisão do pedido.
Last Will/MQTT 5 são propostas até código e evidência verificáveis.
Use tipos válidos, filas limitadas e fronteiras existentes para trabalho bloqueante.
Mantenha mudanças compiláveis e pequenas; atualize ADR/matriz quando afetados.

Valide pela [CONTRIBUTING](../../../CONTRIBUTING.md); mudanças de wire/estado/auth
precisam de negativos e integração pertinente. Relate diff, resultado real e
limitações; não promover versão nem executar próxima feature automaticamente.
