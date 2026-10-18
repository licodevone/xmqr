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
- `MQTT_WSS_BIND` — listener MQTT sobre WSS opcional em IP loopback e porta própria, somente `secure-mtls`; `broker.wss_bind` no TOML é equivalente. Para bind fora de loopback, use `MQTT_WSS_REMOTE_ENABLED=true` ou `broker.wss_remote_enabled=true`, preservando mTLS, credenciais e ACL. Handshakes com `Origin` são recusados.
- `RUST_LOG` — nível de logs, por exemplo `info`.

## Controles implementados

- Timeout de 3 segundos para o handshake TLS e para os primeiros bytes MQTT.
- Primeira leitura limitada a 4 KiB com `AsyncReadExt::take`; o codec ainda deve impor o limite completo de pacote antes de alocar.
- TLS 1.2/1.3 apenas, com provider AWS-LC do rustls e suites AEAD modernas.
- mTLS obrigatório, sem caminho anônimo.
- Limite de conexões concorrentes antes da criação de estado caro.
- P212 em `main`: WSS em `/mqtt` exige subprotocolo `mqtt`, certificado cliente válido, usuário/senha e ACL como o TCP mTLS. TCP e WSS compartilham quota, roteador, estado e geração TLS. Requisições com `Origin` são recusadas; não há acesso remoto ou navegador neste recorte. O pacote 0.39.0 publicado ainda não contém P212.
- Um `tokio::spawn` por cliente e captura de panic na fronteira da tarefa.
- Deadlines explícitos disponíveis para leituras e escritas posteriores.
- Desde0.11.4, shutdown/flushTLS tem deadline3s. Um peer não leitor não
  prende indefinidamente tarefa/vaga após remoção da sessão. Expirar fecha
  a conexão sem prometer flush completo; obrigaçõesQoS duráveis permanecem.
  Veja [P80](../performance-pressure.md).

O certificado do servidor deve incluir `IP:192.168.0.100` no Subject Alternative Name. O Common Name sozinho não é suficiente para clientes TLS modernos. Em containers, confirme se esse IP existe no namespace de rede ou sobrescreva `MQTT_BIND`.

## Rotação local de TLS (P100/B11)

Em Unix, `SIGUSR1` faz o broker reler os caminhos TLS configurados no startup.
Prepare certificado, chave, CA e CRL como um conjunto coerente em arquivos
privados, substitua-os e sinalize o PID conhecido da instância:

```sh
kill -USR1 <PID_DO_BROKER>
```

O broker valida certificado/chave, validade temporal do certificado do servidor
e da CA, emissor, assinatura e período da CRL, e a configuração TLS completa
antes de publicar uma nova geração. Uma falha preserva a geração anterior em
todos os endpoints. Os logs registram apenas aceite/recusa e número da geração,
sem material TLS. Em `tls-password`, a rotação cobre certificado e chave do
servidor; o broker continua sem solicitar certificado do cliente.

A mudança vale para novos handshakes. Conexões TLS existentes prosseguem com a
sessão antiga; para revogação imediata, encerre-as por procedimento operacional
controlado. O sinal não recarrega TOML, bind, ACL, usuários nem estado. `SIGHUP`
continua reservado ao bundle de segurança dinâmica. Uma CRL é opcional no
startup mTLS, mas quando configurada precisa permanecer válida em cada rotação.
Guarde o conjunto anterior para rollback e sinalize novamente após restaurá-lo.

## Limites do controle

Esta camada não substitui validação MQTT. O codec deve limitar Remaining Length, strings, propriedades, filas, inflight e fan-out. O keep-alive negociado determina o deadline depois do CONNECT. Para revogação imediata, distribua CRLs atualizadas ou projete OCSP/um serviço de identidade; apenas confiar na CA não informa certificados revogados.
