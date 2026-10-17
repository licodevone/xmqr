# P183 — CONNACK 0x81 para propriedade MQTT 5 fora de contexto

Entrada: P123/P163 validam propriedades de CONNECT/Will, mas identificadores desconhecidos ou válidos apenas em outro tipo de pacote ainda recebem CONNACK 0x83 genérico. OASIS MQTT 5 §2.2.2 define identificador inválido para o tipo do pacote como Malformed Packet, com motivo 0x81. P181 já diferencia essa classe após CONNACK para SUBSCRIBE/UNSUBSCRIBE. Este prompt precede o código.

Objetivo: responder com CONNACK 0x81 quando um identificador de propriedade não permitido ocorrer em CONNECT ou nas Will Properties, antes de criar sessão, publicar Will ou gravar estado. Preservar 0x8C para método de autenticação desconhecido, 0x86 para PLAIN sem dados e todos os contratos existentes de tamanho, senha/ACL e MQTT 3.1.1. Não classificar duplicatas, UTF-8, truncamento ou quotas neste recorte. Respeitar Maximum Packet Size conhecido; se o limite anunciado for inferior ao CONNACK mínimo, fechar sem resposta.

Aceite: unitários de CONNECT e Will para identificador fora de contexto, sucesso e limite de tamanho; TCP real com CONNACK 0x81, fechamento, ausência de sessão/Will e regressão P123/P163/P180–P181; fmt/test/Clippy/build/licença/distribuição e CI. Atualizar conformance, paridade, checklist e registro como fase 6A parcial. Sem migração nem tag isolada.
