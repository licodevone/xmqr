# P201 — controle MQTT 5 exclusivo do servidor enviado pelo client

Entrada: broker 0.35.0 publicado, P199/P200 aceitos em `main`, fase 6A global aberta. Após CONNACK, um client que envia CONNACK, SUBACK, UNSUBACK ou PINGRESP com cabeçalho válido recebe apenas fechamento porque o decoder cai no erro genérico de tipo não suportado. Este prompt precede qualquer código P201.

Objetivo observável: classificar os quatro pacotes exclusivos de saída do servidor como erro de protocolo do emissor e responder DISCONNECT MQTT 5 `0x82` antes de interpretar corpo ou alterar assinatura, entrega, sessão, retained ou Will. O limite Maximum Packet Size do client continua respeitado pelo escritor existente. Preservar MQTT 3.1.1 e os outros tipos MQTT 5 já suportados; cabeçalhos reservados inválidos e tipo zero ficam fora deste recorte e permanecem na matriz global.

Base: [OASIS MQTT 5.0 §3.2/§3.9/§3.11/§3.13 e §4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html): esses pacotes são respostas do servidor; em erro de protocolo após CONNACK, o servidor deve fechar a conexão e deveria enviar DISCONNECT com motivo quando cabível. Não declarar que a matriz normativa 6A está completa.

Aceite: unitários de codec por tipo, regressão de pacotes válidos/3.1.1; fixture TCP com broker real testa `0x82` e fechamento para cada tipo, nenhuma publicação/assinatura/retained nova e uma conexão normal posterior. Gates fmt, suíte, Clippy, build release, inventário de licenças, contratos de distribuição e CI da fonte exata. Registrar falhas, atualizar checklist/paridade apenas após CI; sem tag/release isolada.
