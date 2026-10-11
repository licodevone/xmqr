# Configuração versionada — implementação P52

Status: implementada no código após P52; não incluída no pacote publicado 0.10.0.
O modo legado MQTT_* e RUST_LOG continua disponível. Use um binário compilado
deste código para experimentar MQTT_CONFIG; preserve o broker.env existente.

## Contrato implementado

MQTT_CONFIG aponta para um TOML com version=1. Sem essa variável, preservar
exatamente o comportamento legado. Com ela, carregar configuração tipada,
rejeitar versão/campos desconhecidos e validar tudo antes de abrir listener ou
estado. Não usar env::set_var nem persistir configuração em WAL/snapshot.

Precedência: defaults seguros < arquivo TOML < variáveis MQTT_* explicitamente
definidas. RUST_LOG continua independente. Caminhos relativos do TOML resolvem
contra a pasta do TOML; caminhos de variáveis preservam a semântica legada.
Uma variável inválida não pode ser ignorada em favor do arquivo.

```toml
version = 1

[broker]
mode = "secure-mtls"
bind = "0.0.0.0:8883"
state_dir = "/var/lib/xmqr"

[tls]
server_cert = "/etc/xmqr/server.crt"
server_key = "/etc/xmqr/server.key"
client_ca = "/etc/xmqr/clients-ca.crt"
# client_crl = "/etc/xmqr/clients.crl"

[security]
bundle = "/etc/xmqr/security.toml"

[monitor]
enabled = false
bind = "127.0.0.1:9090"
```

Os nomes acima são os campos aceitos. Para legado, users_file/acl_file têm equivalência
com MQTT_USERS_FILE/MQTT_ACL_FILE e as mesmas incompatibilidades por perfil.
Senhas e hashes permanecem no arquivo de segurança privado, não neste TOML.

## Limites e etapas

P54 acrescenta, no código ainda não lançado:

```toml
[limits]
max_connections = 64
```

MQTT_MAX_CONNECTIONS prevalece sobre o TOML. Valores aceitos:1..64; padrão64.
Esse limite conta conexões TCP admitidas, incluindo a negociação TLS/MQTT,
não sessões persistentes nem mensagens por segundo. Ao atingir o limite, o
broker fecha a nova conexão antes da negociação MQTT; no MQTT3.1.1 o client
pode observar erro de transporte, sem motivo de quota transmitido no protocolo.
A vaga é liberada quando a tarefa da conexão termina. Alteração exige restart.
Reduzir esse valor não remove sessões persistentes. Quotas de sessões, filas,
inflight, pacote e payload continuam fixas; sua configuração será outra fatia.

Primeira implementação: apenas campos existentes, configuração imutável por
processo, restart para mudanças e rollback removendo MQTT_CONFIG. SIGHUP
continua reservado ao bundle de segurança. Não ativar listener adicional.

Etapa posterior: limites tipados propagados a transporte, ator, codec e store;
preservar defaults 64 conexões/sessões, 32 inflight, 64 offline, 256 assinaturas,
payload4096 e pacote64KiB. Não aumentar só o transporte sem ajustar o documento
durável. Definir limites superiores após benchmarks, não aceitar ilimitado.
Reduzir limites abaixo do estado existente deve falhar sem truncar dados.

## Validação

- Parser aceita exemplo; rejeita campos/versões desconhecidos e tipos errados.
- Override explícito, caminho relativo e modo legado testados sem ambiente global.
- Laboratórios permanecem loopback; monitor permanece loopback.
- Conflitos de TLS/bundle/usuários são recusados sem imprimir valores sensíveis.
- Configuração inválida não cria estado nem abre porta.
- Regressão QoS/retained/sessões/Will, ACL e SIGTERM em diretórios temporários.
- Instalação Ubuntu antiga continua funcionando sem migração obrigatória.
- Documentação anuncia suporte somente após gates e integração aprovados.

O arquivo deve ser UTF-8, regular e ter no máximo 64 KiB. version é obrigatório.
Campos desconhecidos, tipos incorretos e caminhos vazios são recusados. Erros
não reproduzem o conteúdo do TOML. Para ativar em systemd, adicione
MQTT_CONFIG=/etc/xmqr/broker.toml ao broker.env e reinicie o serviço; variáveis
MQTT_* já presentes nesse arquivo continuam prevalecendo sobre o TOML.


## P55 — quotas lógicas (implementação local, aceite Unix pendente)

Campos de [limits] e overrides explícitos:

| TOML | Ambiente | Faixa/padrão |
| --- | --- | --- |
| max_sessions | MQTT_MAX_SESSIONS | 1..64 / 64 |
| max_retained | MQTT_MAX_RETAINED | 1..256 / 256 |
| max_subscriptions | MQTT_MAX_SUBSCRIPTIONS | 1..256 / 256 por sessão |
| max_offline | MQTT_MAX_OFFLINE | 1..64 / 64 por sessão |
| max_inflight | MQTT_MAX_INFLIGHT | 1..32 / 32 por direção por sessão |

Defaults < TOML < ambiente explícito. Zero não significa ilimitado. Valores
inválidos recusam startup antes da criação de estado/listener. max_sessions é
independente de max_connections. Alterações exigem restart; SIGHUP não altera quotas.

Recuperação valida a imagem antes de limpar sessões, replay ou publicação de
Wills; redução incompatível falha sem truncar dados. Volte a valores suficientes
para reiniciar. Os commits usam as mesmas quotas; o formato MQTT v2/leitura v1
não mudou. A recuperação física existente pode reparar cauda WAL incompleta;
isto não autoriza descartar registros comprometidos por redução de quotas.

Ao atingir inflight outbound, mensagens QoS>0 entram na fila offline; ACK libera
espaço e drena até o limite. Offline, sessões, retained, assinaturas e inbound
QoS2 acima da quota recusam o candidato antes do commit/ACK de sucesso, conforme
comportamento anterior. A responsabilidade QoS2 já gravada permanece até sua
conclusão; falhas não confirmam uma transição inexistente. Capacidades internas
do ator/entrega, payload, pacote, tópico e documento permanecem fixas.

Implementado localmente; fmt, Clippy, build e testes portáveis verificados no
Windows. Aceite de recuperação durável/integração Unix ainda BLOCKED nesta
sessão. Consulte o registro P55 antes de usar ou publicar. Não está na release0.10.0.


### P55 rev3 — Will sob saturação

Se uma Will aceita não puder ser publicada por falta de quota, o ator encerra
as conexões e passa a indisponível; a imagem durável original mantém a Will
pendente e as mensagens já aceitas. Não se permite takeover substituir essa
obrigação. Reinicie com quotas suficientes para concluir a publicação. O
listener TCP pode permanecer ligado enquanto o processo está indisponível;
novas operações MQTT falham e readiness não indica saúde. Na recusa durante
recuperação, o writer é encerrado antes do erro de startup, sem expor listener.

Validação isolada Unix: cargo test --locked --test state_limits e
python3 scripts/verify_state_limits.py --broker target/debug/mqtt-broker
--client ../xmqr-client/target/debug/mqtt-client. O harness cobre fronteiras
N/N+1, replay e QoS0/1/2 via CLI independente; não comprova Mosquitto ou TLS.
Testes duráveis continuam pendentes enquanto Linux/WSL não estiver disponível.
