# Autenticação mTLS + usuário/senha + ACL (primeira versão)

Este é um estágio posterior ao
[laboratório MQTT aberto](../laboratorio-mqtt-aberto.md). A primeira aula não
precisa de certificados, usuário, senha ou ACL. Depois dela, evolua em etapas:
usuário/senha, ACL e, por fim, TLS/certificados. O modo seguro atual reúne as
três proteções e continua sendo o padrão quando `MQTT_MODE` não é definido.
Os comandos sem certificado estão em
[laboratório MQTT aberto](../laboratorio-mqtt-aberto.md), e o CRUD está em
[administração de usuários](../administracao-usuarios.md).

Cada cliente deve apresentar **os três fatores de configuração**: certificado
de cliente aceito pela CA local, nome de usuário MQTT e senha MQTT. O broker
vincula o nome de usuário ao SHA-256 do certificado DER apresentado no TLS.
Um certificado válido de outro dispositivo não substitui o certificado
vinculado ao usuário. O `CONNECT` é recusado se qualquer fator falhar.

Após a autenticação, a ACL decide separadamente quais nomes de tópicos podem
ser publicados ou assinados. **Tudo é negado por padrão.** `publish` continua
aceitando somente nomes concretos. `subscribe` aceita nomes exatos e filtros
com `+` e `#`, mas deve conter literalmente o filtro solicitado: `sensores/+`
não autoriza pedir `sensores/#` ou `sensores/um`. A entrega do tópico concreto
também é revalidada contra os filtros da ACL, inclusive na recuperação de
fila offline/inflight. `#` não inclui `$SYS`; isso exige uma concessão explícita
como `$SYS/#`. O tópico surge quando um cliente autorizado publica nele.
Consulte [exemplos e limites](../wildcard-subscriptions.md).

No laboratório, o exemplo permite publicar e assinar `teste/mensagem` com o
mesmo usuário/certificado em dois terminais; os clientes devem ter IDs MQTT
distintos. Em uso real, dê a cada dispositivo seu próprio certificado, usuário
e regras mínimas de tópico.

## Preparar a configuração no Ubuntu/WSL

No projeto, compile o utilitário administrativo:

```bash
cd /caminho/para/xmqr
export CARGO_TARGET_DIR="$HOME/.cache/mqtt-broker-target"
cargo build --locked --release --bin mqtt-admin
```

Para a senha do usuário `lab-device`, execute o programa **sem informar a senha
como argumento**. Ele a pedirá duas vezes sem exibi-la e imprimirá a linha
`password_hash = "..."`:

```bash
"$HOME/.cache/mqtt-broker-target/release/mqtt-admin" hash-password
```

Para obter o vínculo ao certificado público do cliente já criado:

```bash
"$HOME/.cache/mqtt-broker-target/release/mqtt-admin" fingerprint "$HOME/mqtt-lab-certs/client.crt"
```

No terminal WSL, ainda na pasta do projeto, copie os exemplos para a área
privada do usuário:

```bash
mkdir -p "$HOME/.config/mqtt-broker"
cp configs/broker-users.toml.example "$HOME/.config/mqtt-broker/users.toml"
cp configs/broker-acl.toml.example "$HOME/.config/mqtt-broker/acl.toml"
chmod 600 "$HOME/.config/mqtt-broker/users.toml"
nano "$HOME/.config/mqtt-broker/users.toml"
```

No editor, substitua `REPLACE_WITH_64_HEX_DIGITS` pelo SHA-256 mostrado
por `mqtt-admin fingerprint` (mantendo o prefixo `sha256:`) e substitua
`REPLACE_WITH_ARGON2ID_PHC_HASH` pelo hash mostrado por `hash-password`.
Salve com `Ctrl+O`, `Enter`, `Ctrl+X`. O arquivo `acl.toml` de exemplo já
autoriza `lab-device` a publicar e assinar `teste/mensagem`; edite-o se
escolher outro usuário ou tópico. Não copie `client.key` nem `ca.key` para
a pasta do projeto.

O processo de inicialização do broker carrega os dois arquivos e falha se
algum estiver ausente ou inválido. Defina `MQTT_USERS_FILE` e `MQTT_ACL_FILE`
com os caminhos absolutos dos arquivos privados antes de iniciar o broker.
Não há usuário/senha padrão. Os
hashes usam somente Argon2id v19 com parâmetros fixos `m=19456,t=2,p=1`,
evitando que um hash adulterado configure consumo desmedido de memória. Até
quatro verificações ocorrem em paralelo, fora das tarefas assíncronas de rede;
excesso de tentativas recebe falha fechada.

O listener já integra `AuthPolicy` ao `CONNECT`, `PUBLISH` e `SUBSCRIBE`.
`CONNECT` só recebe sucesso após mTLS, senha e vínculo do certificado serem
validados. `SUBSCRIBE` sem permissão recebe `SUBACK` com falha; publicação sem
permissão encerra a conexão (QoS 0 não possui confirmação de publicação).

Exemplo de inicialização **de laboratório** no WSL, depois de criar os arquivos e certificados. Usa a porta `1883`, escolhida para os novos testes e livre na verificação local, sem ocupar a `8883` da instância antiga; execute em um terminal WSL separado. **A conexão nesta porta continua sendo TLS/mTLS**, não MQTT em texto puro:

```bash
cd /caminho/para/xmqr
export CARGO_TARGET_DIR="$HOME/.cache/mqtt-broker-target"
export MQTT_SERVER_CERT="$HOME/mqtt-lab-certs/server.crt"
export MQTT_SERVER_KEY="$HOME/mqtt-lab-certs/server.key"
export MQTT_CLIENT_CA="$HOME/mqtt-lab-certs/ca.crt"
export MQTT_USERS_FILE="$HOME/.config/mqtt-broker/users.toml"
export MQTT_ACL_FILE="$HOME/.config/mqtt-broker/acl.toml"
mkdir -p "$HOME/.local/share/mqtt-broker-lab"
chmod 700 "$HOME/.local/share/mqtt-broker-lab"
export MQTT_STATE_DIR="$HOME/.local/share/mqtt-broker-lab"
export MQTT_BIND="127.0.0.1:1883"
cargo run --locked --release --bin mqtt-broker
```

Use `127.0.0.1` para os primeiros testes; não exponha o serviço à LAN antes
de revisar firewall, limitação de tentativas por IP/dispositivo e certificados
de produção. `MQTT_STATE_DIR` é obrigatório, deve existir no filesystem Linux
local e ser exclusivo desta instância. **Não use `/mnt/c` ou `/mnt/d` para o
estado durável**: as garantias de `fsync`/rename precisam ser verificadas no
filesystem escolhido. O broker agora oferece QoS 0/1/2, retained e sessões
persistentes limitadas, mas ainda não aceita Will nem filtros wildcard.
Quando o broker reinicia com ACL mais restrita, assinaturas e mensagens
pendentes sem permissão são removidas antes de abrir o listener.
