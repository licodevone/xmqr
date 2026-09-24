# Laboratório inicial — MQTT 3.1.1 aberto no computador local

Este é o primeiro exercício do curso: iniciar o broker, assinar um tópico e
publicar mensagens manualmente com QoS 0. Não há TLS, certificados, usuário,
senha ou ACL nesta etapa.

> **Somente aula local:** o modo `open-lab` aceita apenas endereços de loopback.
> Ele não pode ser exposto à rede local, à internet ou usado em produção.

## 1. Compilar uma vez

Abra o Ubuntu/WSL e execute:

```bash
cd /caminho/para/xmqr
export CARGO_TARGET_DIR="$HOME/.cache/mqtt-broker-target"
cargo build --locked --release --bin mqtt-broker --bin mqtt-client
```

## 2. Terminal 1 — iniciar o broker

Abra o primeiro terminal Ubuntu/WSL:

```bash
mkdir -p "$HOME/.local/share/mqtt-broker-open-lab"
chmod 700 "$HOME/.local/share/mqtt-broker-open-lab"

unset MQTT_SERVER_CERT MQTT_SERVER_KEY MQTT_CLIENT_CA MQTT_CLIENT_CRL
unset MQTT_USERS_FILE MQTT_ACL_FILE

export MQTT_MODE="open-lab"
export MQTT_BIND="127.0.0.1:1883"
export MQTT_STATE_DIR="$HOME/.local/share/mqtt-broker-open-lab"
export RUST_LOG="info"

"$HOME/.cache/mqtt-broker-target/release/mqtt-broker"
```

Resultado esperado no Terminal 1:

```text
OPEN LAB listener started without TLS, authentication or ACL; loopback only
```

Deixe o broker aberto. A porta `1883` deste exercício usa MQTT TCP simples.
Se aparecer `Address already in use`, outra instância já ocupa a porta; encerre
essa instância conscientemente no terminal em que ela foi iniciada antes de
repetir o comando. Não execute dois brokers na mesma porta.

## 3. Terminal 2 — iniciar o assinante

Abra um segundo terminal Ubuntu/WSL:

```bash
"$HOME/.cache/mqtt-broker-target/release/mqtt-client" sub \
  --open-lab \
  --topic 'aula/mensagem' \
  --host 127.0.0.1 \
  --port 1883 \
  --client-id 'aluno-sub' \
  --qos 0
```

Resultado esperado no Terminal 2:

```text
Assinatura ativa. Aguardando mensagens; Ctrl+C para sair.
```

O assinante continua aberto. Não há etapa separada para criar o tópico: ele
passa a existir quando uma mensagem é publicada.

## 4. Terminal 3 — publicar manualmente

Abra um terceiro terminal Ubuntu/WSL:

```bash
"$HOME/.cache/mqtt-broker-target/release/mqtt-client" pub \
  --open-lab \
  --topic 'aula/mensagem' \
  --message 'Olá, MQTT!' \
  --host 127.0.0.1 \
  --port 1883 \
  --client-id 'aluno-pub' \
  --qos 0
```

Resultado esperado no Terminal 3:

```text
PUBLISH QoS 0 enviado; o protocolo nao confirma entrega ao assinante.
```

Resultado esperado no Terminal 2:

```text
topico="aula/mensagem" qos=0 retain=false mensagem="Olá, MQTT!"
```

Repita o comando de publicação trocando somente `--message` para enviar novos
valores manualmente. IDs de cliente simultâneos devem ser diferentes.

## 5. Encerrar

O publicador encerra após o envio. Pressione `Ctrl+C` primeiro no assinante e
depois no broker.

## Verificação rápida de erros

- `Connection refused`: o broker não está rodando ou a porta não é `1883`.
- Erro de modo aberto: confirme `MQTT_MODE=open-lab` e `127.0.0.1`.
- Variáveis de segurança presentes: execute os dois comandos `unset` do passo 2.
- O assinante não recebe: confirme que tópico, porta e IDs estão iguais aos
  exemplos, exceto que os dois IDs devem permanecer distintos.
- Não misture o diretório `mqtt-broker-open-lab` com o estado do modo seguro.

