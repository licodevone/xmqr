# Retained e Last Will - 0.6.0 local

Retained ja existia na 0.5: ultimo valor por topico, replay para nova assinatura,
deduplicacao wildcard, QoS minimo e exclusao por payload vazio. A 0.6 integra
Will ao mesmo roteamento, ACL e persistencia, preservando limite1024 bytes UTF-8.

Will pertence a conexao aceita, independentemente de CleanSession. CONNECT
valida flags, topico sem wildcard, payload binario ate4096 e QoS0/1/2. ACL negada
recusa CONNECT com CONNACK0x05. Registro duravel precede CONNACK de sucesso.
Queda de socket, erro de protocolo, keep-alive e takeover do mesmo dono publicam
Will; DISCONNECT cancela antes da remocao duravel. Geracao antiga nao publica
novamente. ACL e revalidada na publicacao/restore; revogacao descarta Will.

Will pendente e mensagem resultante/remocao sao uma transicao duravel. Apos
crash do broker, restart publica antes do listener, incluindo retained/offline
QoS>0. Nao promete envio durante ausencia do broker nem prova perda de energia.
No shutdown abrupto SIGTERM/kill, Wills pendentes ficam para o restart. Nao ha
novo controlador de shutdown gracioso neste marco. Cancelamento de task/panic agenda cleanup pelo guard da conexao; se o runtime
tambem encerra, o Will duravel e recuperado no restart.

Quotas atuais e fsync continuam obrigatorios. Falha de armazenamento ou quota
na transicao nao apaga Will nem confirma estado inexistente: erro interrompe
fluxo; restart pode falhar fechado se a causa persistir. Nao ampliar quotas
nem editar WAL manualmente. Payload/credenciais nao sao publicados em logs.

## Compatibilidade e rollback

Documento MQTT v2 adiciona pending_wills, com leitura de v1. WAL/snapshot e
chave do agregado permanecem v1. Binario0.5 nao entende documento v2: antes
de testar/atualizar, pare e preserve backup COMPLETO anterior em outro diretorio.
Rollback usa esse backup e binario anterior, nao UNSUBSCRIBE parcial. Nenhum
estado real foi migrado por esta implementacao; testes usam diretorios temporarios.

## Validacao reproduzivel

Execute fmt/test/clippy/inventario e build --bins. Depois, em Linux/WSL:

```sh
python3 scripts/verify_last_will.py --broker target/debug/mqtt-broker --client target/debug/mqtt-client
```

Fixtures socket independentes e cliente rumqttc proprio; portas loopback e
estado temporarios, sem Mosquitto. Nao equivale a interoperabilidade Mosquitto
ou TLS/mTLS externa. Evidencias reais em prompts/registros/P42-0.6.0.md.
Fonte normativa: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html
