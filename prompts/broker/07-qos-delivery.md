> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/07-qos-delivery.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — entrega QoS 0, 1 e 2

Modele QoS por direção e packet identifier. Entregue em incrementos: QoS 0 fim a fim; QoS 1 com retransmissão e DUP; QoS 2 com estados PUBLISH/PUBREC/PUBREL/PUBCOMP.

Especifique alocação e reciclagem de identifiers, receive maximum/inflight, ordenação, duplicatas, reconexão, timeout e backpressure. Para cada transição, declare se e quando o estado precisa ser durável antes do ACK.

Teste perda de cada pacote, duplicação, reordenação permitida/proibida, restart em cada ponto, esgotamento de identifier e consumidor lento. Não use “exactly once” como garantia de negócio além do que o protocolo oferece.
