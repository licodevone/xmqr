# Camada de transporte MQTT segura

Este documento descreve o modo padrão `secure-mtls`. O modo didático explícito
`MQTT_MODE=open-lab` usa TCP simples, mas o broker o restringe tecnicamente a
um endereço de loopback. Consulte o
[laboratório MQTT aberto](../laboratorio-mqtt-aberto.md). Nunca use esse modo
em rede local, internet ou produção.

O listener aceita somente TLS com certificado de cliente obrigatório. A cadeia do dispositivo é validada contra `MQTT_CLIENT_CA`; uma CRL PEM pode ser exigida por meio de `MQTT_CLIENT_CRL`.

## Variáveis

- `MQTT_BIND` — endereço, padrão `192.168.0.100:8883`.
- `MQTT_SERVER_CERT` — cadeia PEM do servidor, leaf primeiro.
- `MQTT_SERVER_KEY` — chave privada PEM do servidor, com permissões restritas.
- `MQTT_CLIENT_CA` — CA raiz/intermediária confiável para dispositivos.
- `MQTT_CLIENT_CRL` — CRL PEM opcional; sem ela não há informação offline de revogação.
- `RUST_LOG` — nível de logs, por exemplo `info`.

## Controles implementados

- Timeout de 3 segundos para o handshake TLS e para os primeiros bytes MQTT.
- Primeira leitura limitada a 4 KiB com `AsyncReadExt::take`; o codec ainda deve impor o limite completo de pacote antes de alocar.
- TLS 1.2/1.3 apenas, com provider AWS-LC do rustls e suites AEAD modernas.
- mTLS obrigatório, sem caminho anônimo.
- Limite de conexões concorrentes antes da criação de estado caro.
- Um `tokio::spawn` por cliente e captura de panic na fronteira da tarefa.
- Deadlines explícitos disponíveis para leituras e escritas posteriores.

O certificado do servidor deve incluir `IP:192.168.0.100` no Subject Alternative Name. O Common Name sozinho não é suficiente para clientes TLS modernos. Em containers, confirme se esse IP existe no namespace de rede ou sobrescreva `MQTT_BIND`.

## Limites do controle

Esta camada não substitui validação MQTT. O codec deve limitar Remaining Length, strings, propriedades, filas, inflight e fan-out. O keep-alive negociado determina o deadline depois do CONNECT. Para revogação imediata, distribua CRLs atualizadas ou projete OCSP/um serviço de identidade; apenas confiar na CA não informa certificados revogados.
