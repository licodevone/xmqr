# Prompt — assinaturas, matching e roteamento

Implemente validação de topic names e filters, incluindo `+`, `#`, níveis vazios, limite UTF-8 e regra de tópicos iniciados por `$`. Não normalize strings durante matching ou autorização.

Escolha o índice com base em operações e cardinalidades do contexto. Defina atomicidade de SUBSCRIBE/UNSUBSCRIBE, deduplicação quando múltiplas assinaturas da mesma sessão casam, QoS efetivo e fan-out com backpressure.

Comece por tópicos exatos e QoS 0; adicione wildcards somente com testes de propriedades e vetores de borda. Meça custo de inserção, remoção e match para árvores largas e profundas.

