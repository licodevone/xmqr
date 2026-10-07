> **Adaptação XMQR — 2026-10-07.** Histórico de escopo da origem, sem prova de execução no XMQR. Não reaplicar sobre o código existente. Para validar o snapshot atual, usar broker/36 e clients/24.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/25-durable-mqtt-state-contract.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — contrato durável do estado MQTT

Este é o primeiro passo depois do MVP QoS 0 (`22`–`24`). Leia as instruções locais, se existirem, `prompts/broker/00-project-context.md`, `prompts/broker/07-qos-delivery.md`, `prompts/broker/08-sessions-retained-will-persistence.md`, `docs/architecture/adr-0001-durable-persistence.md` e o código real. Use MQTT **3.1.1**, não semânticas de expiração/Receive Maximum de MQTT 5. Referência normativa: [OASIS MQTT 3.1.1, §§ 3.1.2.4, 4.1 e 4.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

## Entrega

1. Defina tipos e versão de serialização para `SessionState`, assinaturas, fila offline, inflight recebido/enviado e retained **separado da sessão**. Identifique cada estado por cliente, direção, packet identifier e geração da conexão. Proíba credenciais, chaves privadas e certificado integral no WAL; vincule o `client_id` à identidade mTLS + usuário autenticado no reencontro.
2. Escolha **um** método atômico para mutações relacionadas: um registro por agregado ou transação multichave no escritor exclusivo. A camada chave/valor existente garante somente uma operação por commit; não presuma atomicidade de vários `put`/`delete`. Versione o envelope, imponha limites de tamanho/quantidade e rejeite formato desconhecido sem reinterpretá-lo.
3. Declare uma tabela `evento → mudança em memória → commit WAL/fsync → resposta MQTT`. Depois de erro de persistência, falhe fechado: não envie PUBACK/PUBREC/PUBCOMP/SUBACK/CONNACK de retomada que pressuponha estado perdido. Nenhum I/O de disco ou lock bloqueante no hot path Tokio; use a fronteira assíncrona e fila limitada do escritor.
4. Desenhe recuperação e migração do formato anterior: snapshot versionado, checksum, cauda WAL incompleta, corrupção completa, rollback sobre cópia e preservação dos arquivos originais. Especifique quando snapshot/compactação é segura, incluindo identificadores inflight ainda em uso.
5. Registre quotas por sessão, retenção, fila offline, inflight, disco e memória e política observável quando cada quota esgotar. Diferencie garantia após queda de processo, queda de VM e perda de energia; não extrapole a cobertura dos testes.

## Prova antes de avançar

Teste codec estável de estado (versão antiga/atual/desconhecida), idempotência de replay, crash injetado antes/depois do commit e do snapshot, corrupção, disco cheio e duas operações logicamente relacionadas. Atualize ADR e matriz de conformidade somente para comportamentos implementados. A saída deve declarar contrato de durabilidade, plano de migração, limites, testes executados e lacunas. Use `prompts/contrato-base.md`, `prompts/contrato-base.md`, `prompts/contrato-base.md` e `prompts/contrato-base.md`.
