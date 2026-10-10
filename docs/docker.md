# Imagem Docker do XMQR broker

A imagem é construída localmente a partir do código e do `Cargo.lock`. O build
usa Rust 1.99.0 para corresponder à validação Linux atual; a etapa final Debian
slim contém apenas os dois binários, dependências de runtime e avisos de licença.
O processo roda como UID/GID 10001. Nenhum certificado ou credencial é copiado
para a imagem.

```sh
docker build -t xmqr-broker:0.10.0 .
docker image inspect xmqr-broker:0.10.0 --format '{{.Config.User}}'
```

O padrão é `secure-mtls` na porta 8883, vinculado a todas as interfaces do
container. Para iniciar, forneça certificado, chave, CA e bundle de segurança
em arquivos externos. Os arquivos devem ser legíveis pelo usuário 10001; o
bundle exige modo 0600 e proprietário igual ao UID efetivo do processo. Um
exemplo de configuração está em
[`docs/security/dynamic-security.md`](security/dynamic-security.md).

```sh
docker volume create xmqr-state
docker run -d --name xmqr-broker \
  -p 8883:8883 \
  -v xmqr-state:/var/lib/xmqr \
  -v "$PWD/secrets:/run/secrets:ro" \
  -e MQTT_SERVER_CERT=/run/secrets/server.crt \
  -e MQTT_SERVER_KEY=/run/secrets/server.key \
  -e MQTT_CLIENT_CA=/run/secrets/clients-ca.crt \
  -e MQTT_SECURITY_BUNDLE=/run/secrets/security.toml \
  xmqr-broker:0.10.0
```

O volume guarda WAL, snapshot e marcador do perfil. Não compartilhe o mesmo
volume entre brokers concorrentes. Bind mounts no Windows podem não preservar
UID/permissões POSIX necessárias ao bundle; prefira volume Docker para os dados
e monte os arquivos de segurança depois de ajustar dono/permissões no filesystem
Linux da VM Docker. O monitor HTTP opcional continua preso ao loopback dentro do
container, por isso não publique a porta 9090 para o host.

O perfil `open-lab` continua restrito a loopback no container; publicar `1883`
não o torna acessível de fora e essa limitação é intencional. Não o use como
atalho para rede externa. Para tráfego entre containers use `secure-mtls` e
certificados cujos SANs correspondam aos nomes usados pelos clientes.

`mqtt-admin` está na mesma imagem. Backup/verify/restore exigem broker parado;
execute o utilitário com o volume do estado anexado, e grave o backup num volume
ou diretório separado. SHA-256 detecta corrupção acidental, mas não autentica o
backup. A imagem inclui o texto MIT e o inventário de dependências; ao redistribuir,
preserve também os avisos/licenças de terceiros aplicáveis aos componentes.

```sh
docker run --rm --entrypoint /usr/local/bin/mqtt-admin xmqr-broker:0.10.0 --help
```

Não há `HEALTHCHECK` nesta imagem: o endpoint `/ready` é opcional e loopback, e
um teste superficial do processo não demonstraria readiness MQTT ou durabilidade.
As tags acima são nomes locais de imagem; esta tarefa não envia imagem a registry
nem cria tags Git.
