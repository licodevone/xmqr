# Prompt — entrega QoS 0, 1 e 2

Modele QoS por direção e packet identifier. Entregue em incrementos: QoS 0 fim a fim; QoS 1 com retransmissão e DUP; QoS 2 com estados PUBLISH/PUBREC/PUBREL/PUBCOMP.

Especifique alocação e reciclagem de identifiers, receive maximum/inflight, ordenação, duplicatas, reconexão, timeout e backpressure. Para cada transição, declare se e quando o estado precisa ser durável antes do ACK.

Teste perda de cada pacote, duplicação, reordenação permitida/proibida, restart em cada ponto, esgotamento de identifier e consumidor lento. Não use “exactly once” como garantia de negócio além do que o protocolo oferece.

