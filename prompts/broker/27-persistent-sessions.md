> **Adaptação XMQR — 2026-10-07.** Histórico de escopo da origem, sem prova de execução no XMQR. Não reaplicar sobre o código existente. Para validar o snapshot atual, usar broker/36 e clients/24.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/27-persistent-sessions.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — sessões persistentes MQTT 3.1.1

Execute após `25` e a fatia QoS 1 `26`. Use o [OASIS MQTT 3.1.1, §§ 3.1.2.4, 3.2.2.2, 3.8.4, 3.10, 4.1 e 4.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html). `CleanSession=0` significa sessão armazenada sem prazo de expiração MQTT 5; não invente TTL protocolar implícito.

## Entrega

1. Separe `SessionState` persistente de `ConnectionState` transitório. Para `CleanSession=0`, crie/retome por `client_id`, restore assinaturas e fila QoS 1/2 e responda CONNACK com `Session Present` correto. Para `CleanSession=1`, apague estado anterior do mesmo ID atomicamente e responda SP=0. Recuse `client_id` vazio com CleanSession=0 conforme § 3.1.3.
2. Exija reautenticação mTLS + usuário/senha em cada conexão. Defina o vínculo estável entre `client_id` e identidade; outra identidade não herda sessão, fila ou subscriptions. Em takeover do mesmo ID, invalide a geração antiga antes de expor a nova; uma tarefa antiga não pode remover ou gravar a sessão nova.
3. Persista alterações de assinatura, `UNSUBSCRIBE`/`UNSUBACK`, fila offline QoS>0 e estados inflight nos dois sentidos. Respeite o QoS concedido; adote e documente como política local não enfileirar QoS 0 offline. Ao retomar, reenvie PUBLISH/PUBREL pendentes com packet identifiers originais (§ 4.4). Defina a ordem entre replay e novas publicações.
4. Delimite fila offline, número de sessões, assinaturas, idade operacional, disco e inflight. Se uma quota impedir o aceite durável, não confirme um estado inexistente. Se houver política administrativa de expiração/remoção, registre-a como extensão local, com observabilidade e sem chamá-la de semântica MQTT 5.
5. Use o contrato e a migração de `25`: commit atômico do agregado antes dos ACKs pertinentes, recuperação determinística e snapshot seguro. Não carregue toda a fila offline sem limite na memória.

## Gate

Teste sessões novas/existentes (SP=0/1), CleanSession=1 descartando estado, desconexão e restart, assinante offline recebendo QoS>0, `UNSUBSCRIBE`, perda de ACK, takeover concorrente, certificado/usuário trocado, quota e crash em cada fronteira de commit. Verifique interoperabilidade com clientes externos e cite cláusulas nos testes. Atualize ADR, matriz de conformidade e instruções operacionais; declare sem ambiguidade o que permanece sem suporte (por exemplo, QoS 2 até o prompt `28`).
