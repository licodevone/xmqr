# Configuração versionada — implementação P52

Status: incluída no pacote0.11.0; aceita em Ubuntu26/WSL na fase1(P61).
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
# additional_binds = ["127.0.0.1:8884"] # P96, apenas secure-mtls
state_dir = "/var/lib/xmqr"
# server_keep_alive_seconds = 60 # MQTT 5, teto opcional de Keep Alive

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

P162 acrescenta `[broker].server_keep_alive_seconds` ou
`MQTT_SERVER_KEEP_ALIVE_SECONDS`, opcional e validado em 1..65535 no startup.
O ambiente explícito prevalece sobre o TOML. Em MQTT 5, se o CONNECT pede zero
ou um Keep Alive maior que o teto, o CONNACK de sucesso anuncia Server Keep
Alive `0x13` e o broker aplica 1,5 vez o valor anunciado ao prazo de
inatividade. Se o cliente já pede valor menor ou igual, não há propriedade
nova. Um Maximum Packet Size insuficiente para anunciar o valor exigido recusa
o CONNECT com 0x95 antes de abrir sessão. MQTT 3.1.1 e a configuração ausente
conservam o comportamento anterior. A opção exige restart e não migra estado.

## Limites e etapas

P54 acrescenta, incluído na versão0.11.0:

```toml
[limits]
max_connections = 64
```

MQTT_MAX_CONNECTIONS prevalece sobre o TOML. Valores aceitos:1..64; padrão64.

Esse limite conta conexões TCP/WS admitidas, incluindo a negociação TLS/MQTT,
não sessões persistentes nem mensagens por segundo. Ao atingir o limite, o
broker fecha a nova conexão antes da negociação MQTT; no MQTT3.1.1 o client
pode observar erro de transporte, sem motivo de quota transmitido no protocolo.
A vaga é liberada quando a tarefa da conexão termina. Alteração exige restart.
Reduzir esse valor não remove sessões persistentes. Quotas de sessões, filas,
inflight, pacote e payload continuam fixas; sua configuração será outra fatia.

No perfil `open-lab`, `MQTT_WS_BIND=127.0.0.1:8083` (ou `ws_bind` na seção
`[broker]` do TOML) ativa um listener WebSocket MQTT em `/mqtt` com
subprotocolo `mqtt`. O endereço deve ser IP loopback com porta positiva,
distinto de `MQTT_BIND`. Nenhum listener WS é ativado por padrão; os demais
perfis rejeitam essa opção. TCP e WS compartilham a quota
`MQTT_MAX_CONNECTIONS` e o estado do router. WSS permanece pendente.
Handshakes com `Origin` são recusados neste recorte sem autenticação; uso por
navegador exigirá uma política de origem própria.

Configuração TOML imutável por processo; mudanças de bind exigem restart. SIGHUP
continua reservado ao bundle de segurança. SIGUSR1 relê apenas os arquivos TLS
referenciados no startup; consulte a [rotação TLS](../security/secure-transport.md).

P96 permite até três `additional_binds` TCP mTLS, com endereço e porta explícitos.
O primário e os adicionais compartilham TLS, política, roteador, estado,
monitoramento, IDs e `max_connections`; falha de qualquer bind impede o início.
Porta zero, duplicata, wildcard adicional e sobreposição com primário wildcard
são recusados. Os modos de laboratório não aceitam endpoints adicionais.
Cada alteração de endereço exige restart; remova `additional_binds` para voltar
ao listener único. A rotação de CA/certificado/CRL por SIGUSR1 publica uma
geração comum aos endpoints.

P101 permite políticas **estáticas** por endpoint mTLS. No TOML, declare
`[[endpoint_policies]]` uma vez para cada bind, inclusive o primário:

```toml
[[endpoint_policies]]
bind = "0.0.0.0:8883"
users_file = "/etc/xmqr/primary-users.toml"
acl_file = "/etc/xmqr/primary-acl.toml"

[[endpoint_policies]]
bind = "127.0.0.1:8884"
users_file = "/etc/xmqr/secondary-users.toml"
acl_file = "/etc/xmqr/secondary-acl.toml"
```

O segundo bind também deve constar em `broker.additional_binds`. O broker
recusa mapeamento parcial, duplicado ou estranho, arquivos inválidos, modo
diferente de `secure-mtls` e mistura com `security.bundle` ou os campos globais
`users_file`/`acl_file`. O roteador e o limite continuam compartilhados;
usuários e IDs de client iguais em endpoints distintos são isolados no estado
durável. O estado recebe perfil `secure-mtls-scoped` e exige diretório próprio:
não há migração implícita do perfil compartilhado. IDs de client nesse perfil
têm até 254 bytes antes do prefixo interno de dois bytes. TLS e rotação SIGUSR1
permanecem comuns aos endpoints; arquivos de política estática exigem restart.

P97 acrescenta o modo opt-in `tls-password` no listener único. Configure
`[broker] mode = "tls-password"`, `state_dir` próprio, `[tls] server_cert` e
`server_key` e, em `[security]`, `users_file` com hashes Argon2id e `acl_file`
com permissões explícitas, ou o bundle privado. `client_ca` e `client_crl`
são recusados nesse modo; o servidor não solicita certificado de cliente.
Senha/usuário são obrigatórios em CONNECT, protegidos por TLS, e a ACL segue
deny-by-default. O client usa `--tls-password --ca CA.crt --username USUARIO`
e senha interativa ou `--password-file` privado. SAN e validade do servidor
continuam verificados. O diretório de estado `tls-password` não pode ser
reutilizado por `secure-mtls` ou laboratório; não há migração de WAL.

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


## P55 — quotas lógicas (aceitas no Ubuntu26 pela fase1/P61)

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
Testes duráveis foram aprovados no Ubuntu26/WSL emP61, incluindo12 imagens
v1/v2, Will saturada e7 cenários reais. Isso não homologa outras plataformas.


## P58 — pacote completo e payload

O teto fixo64KiB significa65536 bytes do pacote MQTT completo: primeiro byte,
bytes reais de Remaining Length e corpo. O broker recusa excesso assim que
o cabeçalho declara o tamanho, sem aguardar o corpo. Um pacote com Remaining
Length65532 codificado em3 bytes ocupa exatamente65536;65533 ocupa65537 e
é recusado. Vários pacotes concatenados têm limites individuais.

Payload PUBLISH e Will permanece4096 bytes, tópico/filtro1024 UTF-8; não há
configuração TOML/ambiente para ampliar esses tetos. A CLI independente usa
o mesmo contrato. A correção restringe os4 bytes extras aceitos no framing
anterior; formato durável, ACL, QoS e TLS não mudam. Negativos wire próprios
aprovados no Windows não comprovam recuperação Unix ou interop externa.
Veja [registro P58](../../prompts/registros/P58-pacote-completo.md).
