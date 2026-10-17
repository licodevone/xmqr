# P139 rev4 — Topic Alias de saída MQTT 5

Entrada: P138 aceito em `main`, broker 0.20.0 publicado; 6C ainda aberta. Criar este prompt antes do código.

Objetivo: respeitar Topic Alias Maximum do CONNECT MQTT 5 do assinante (padrão zero) ao enviar PUBLISH. Usar no máximo 16 associações por conexão para limitar memória. Na primeira entrega de um tópico, enviar nome completo e alias; em entregas seguintes nessa conexão, enviar nome vazio com o alias. Não incluir alias em MQTT 3.1.1 ou quando o cliente anunciar zero. Registrar a associação somente depois de escrita bem-sucedida. Reconexão, takeover e restart começam sem associações, incluindo retransmissão QoS. Se o primeiro pacote com alias exceder Maximum Packet Size mas a forma sem alias couber, enviar sem alias; manter descartes QoS duráveis já definidos em P136. ACK, retained, expiração, ACL e Receive Maximum continuam operando sobre o tópico completo interno.

Aceite: parser CONNECT (zero, máximo, duplicata, truncado), vetores de PUBLISH com propriedade alias, integração TCP QoS0/1/2, retained, limite de pacote 5/10/13 e reset de conexão, interoperabilidade Mosquitto e client independente, regressões P134/P136 e 3.1.1, fmt/testes/Clippy/build/CI. Documentar recorte de 6C e suas limitações, sem marcar a fase global completa. Commit/push após evidência. Sem novo ensaio físico ESP32.

Revisão após o primeiro gate: compilação de testes falhou (E0027) em quatro vetores que fazem correspondência exata de `Mqtt5ConnectProperties::Supported` sem o novo campo `topic_alias_maximum`. Atualizar os vetores para afirmar zero por padrão e o valor negociado, repetindo a compilação e a suíte antes da integração.

Revisão após o segundo gate: 159 testes da biblioteca passaram (6 ignorados), mas Clippy recusou a assinatura do novo encoder por quatro booleanos (`retain`, `dup`, `mqtt5`, `omit_topic`). Substituir o par alias/omissão por enum explícito `None/Establish/Use`, repetir Clippy e testar os bytes de cada forma. Não suprimir o lint.

Revisão após o terceiro gate: vetores unitários e integração TCP raw passaram até o assinante Mosquitto. Esse assinante recebeu a primeira entrega e fechou com erro de protocolo na segunda entrega abreviada. Não aceitar a interoperabilidade ainda. Capturar o fluxo e comparar com a regra OASIS e o comportamento de Mosquitto 2.0.22; corrigir bytes/estado se for defeito XMQR. Se o cliente externo não suportar a forma válida, registrar o limite com reprodução independente e não alegar interop dessa direção.
