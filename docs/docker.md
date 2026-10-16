# Imagem Docker do XMQR broker

## Distribuição atual 0.16.0 — MQTT 5 inicial experimental

Imagens numeradas `lepinheiro100/xmqr-broker:0.16.0` e
`lepinheiro100/xmqr-admin:0.16.0` publicadas com os digests, fontes e hashes
registrados em [P117](../prompts/registros/P117-release-0.16.0.md). O admin
desta imagem é o CLI legado do pacote broker; o `xmqr-admin` independente
continua 0.4.0. A [prerelease](https://github.com/licodevone/xmqr/releases/tag/v0.16.0)
contém os exports e checksums. Nenhum `latest` foi movido.

## Histórico 0.11.6 — fase3 experimental

Broker e mqtt-admin legado0.11.6 publicados no Hub; fonte dos artefatos
abbe38ca6c041f7328e85054506a4eed22c74c41. Client0.9.0 tem imagem independente.
O novo xmqr-admin continua0.1.0, no repositório/imagem admin-ui próprios;
não é a imagem xmqr-admin abaixo. MQTT3.1.1, sem MQTT5 nesta entrega.

```sh
docker pull lepinheiro100/xmqr-broker:0.11.6
docker pull lepinheiro100/xmqr-admin:0.11.6
docker run --rm --network none --read-only --cap-drop=ALL lepinheiro100/xmqr-broker:0.11.6 --version
docker run --rm --network none --read-only --cap-drop=ALL lepinheiro100/xmqr-admin:0.11.6 --version
```

Digests de índice OCI conferidos após push e usados em pull/run de versão:

- broker: `sha256:576de5ddc2dc2f74cbb2f243126d8c36668784f110ed0da03a05df8435352f97`;
- admin legado: `sha256:8893fae7624336bd150eb7ae8fc4933752673c2f00e7bab509c6416985307c72`.

A [prerelease0.11.6](https://github.com/licodevone/xmqr/releases/tag/v0.11.6)
contém .debUbuntu26amd64, dois exports Docker tar.gz, manifests/checksums e
relatórios finitos. Confira SHA antes de `docker load -i ARQUIVO.tar.gz`.
Esses tar.gz não são executáveis nativos. Bookworm é o alvo das imagens;
não instalar o .debUbuntu nelas. Certificados, credenciais e estado são externos.

Para reconstruir o código atual, use uma tag LOCAL ainda inexistente; nunca
substitua uma versão publicada. Commit documental atual terá revision própria,
não deve ser apresentado como fonte do artefato já publicado de abbe.

```sh
docker build --platform linux/amd64 --build-arg VERSION=0.11.6 --build-arg VCS_REF="$(git rev-parse HEAD)" --target runtime -t xmqr-broker:0.11.6-local .
docker build --platform linux/amd64 --build-arg VERSION=0.11.6 --build-arg VCS_REF="$(git rev-parse HEAD)" --target admin -t xmqr-admin-legacy:0.11.6-local .
```

Seções anteriores abaixo são históricas; seus comandos de build não devem
ser executados no HEAD atual nem usados para sobrepor imagens publicadas.
Para recursos aceitos/limites, consulte [fase3](phase3-acceptance.md).

## Histórico do marco 0.11.4 — broker e admin no Docker Hub

PatchP80 limita shutdownTLS3s após peer lento; quotas/MQTT/estado preservados.
Client permanece0.8.1; fase2 integral depende do teste físicoE01.

Distribuição P78/C42: imagens Linux/amd64 versionadas no namespace autorizado
lepinheiro100; admin acompanha a versão do broker. O .deb Ubuntu26 contém os
dois executáveis. A imagem admin é própria, não inicia broker e não contém o
binário mqtt-broker. Comandos deste marco pressupõem publicação aceita; confira
a tag/digest no Hub e o manifesto da release antes de usar.

```sh
docker pull lepinheiro100/xmqr-broker:0.11.4
docker pull lepinheiro100/xmqr-admin:0.11.4
docker run --rm --network none --read-only --cap-drop=ALL lepinheiro100/xmqr-broker:0.11.4 --version
docker run --rm --network none --read-only --cap-drop=ALL lepinheiro100/xmqr-admin:0.11.4 --version
```

Para construir, passe a versão do manifest e o commit limpo aceito. O último
alvo continua sendo o broker; --target admin seleciona o utilitário. O build
falha se VERSION não corresponder à saída do binário. O contexto contém somente
Cargo.toml/lock, fontes, licença e inventário de licenças, sem arquivos do curso,
estado ou certificados. Tags Git/Hub antigas não serão alteradas; latest não
é atualizado por inferência.

```sh
docker build --platform linux/amd64 --build-arg VERSION=0.11.4 --build-arg VCS_REF="$(git rev-parse HEAD)" --target runtime -t lepinheiro100/xmqr-broker:0.11.4 .
docker build --platform linux/amd64 --build-arg VERSION=0.11.4 --build-arg VCS_REF="$(git rev-parse HEAD)" --target admin -t lepinheiro100/xmqr-admin:0.11.4 .
```

O runtime das imagens é DebianBookworm, compilado para suas bibliotecas; o
.deb nativo é Ubuntu26 amd64. Não instale o .deb Ubuntu na imagem Bookworm.
Não há homologação nova de Ubuntu24, arm64 ou Windows nativo.

Backup/restore do admin exige broker parado e volume com dono10001, além de
destino novo. Monte o estado e o destino em volumes apropriados; não use
dados reais num teste. O arquivo de senha/bundle permanece externo e privado.
Para admin verify/restore com --read-only, monte também um tmpfs limitado:
`--tmpfs /tmp:rw,noexec,nosuid,size=128m,mode=1777`. A verificação abre uma
cópia temporária para validar recuperação, sem modificar o backup original.
Ajuste a capacidade do tmpfs ao backup e ao orçamento de memória; espaço
insuficiente é erro, não sucesso parcial. O rootfs permanece read-only.
Para a conexão normal use mTLS, SAN correto e o procedimento de volumes
abaixo, substituindo a imagem local pelo nome completo do Hub.

Artefatos .deb, imagens tar.gz e hashes ficam na prerelease v0.11.4.
scripts/release_assets.py exporta somente imagens esperadas com usuário,
entrypoint, versão e revision corretos, sem publicar automaticamente.
O manifesto identifica o commit Git e cada SHA-256. Digest remoto e resultados
de validação acompanham os anexos; comparar com a release antes do deploy.
O [plano de paridade](plano-paridade-mosquitto.md) distingue funções existentes
das planejadas. As seções P63 abaixo descrevem o histórico, não a publicação atual.

## Histórico de distribuição local P63/P64

A imagem é construída localmente a partir do código e do `Cargo.lock`. O build
usa Rust 1.99.0 para corresponder à validação Linux atual; a etapa final Debian
slim contém apenas os dois binários, dependências de runtime e avisos de licença.
O processo roda como UID/GID 10001. Nenhum certificado ou credencial é copiado
para a imagem.

```sh
docker build -t xmqr-broker:0.11.2 .
docker image inspect xmqr-broker:0.11.2 --format '{{.Config.User}}'
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
  xmqr-broker:0.11.2
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
docker run --rm --entrypoint /usr/local/bin/mqtt-admin xmqr-broker:0.11.2 --help
```

Não há `HEALTHCHECK` nesta imagem: o endpoint `/ready` é opcional e loopback, e
um teste superficial do processo não demonstraria readiness MQTT ou durabilidade.
As tags acima são nomes locais de imagem; esta tarefa não envia imagem a registry
nem cria tags Git.

Esse texto descreve o comando de build local. A distribuição P63 publica
arquivos nas releasesGitHub e tagsGit separadamente; não faz push emregistry.

## Distribuição P63/C40 — linux/amd64

As releases0.11.1/0.7.1 incluem imagem exportada tar.gz, checksum e pacote
.deb Ubuntu26amd64. A imagem DebianBookworm contém seu runtime; isso permite
executar em hosts Linux com Docker e arquitetura compatíveis, sem homologar
todas as distribuições ou arm64. Não há publicação em registry nesta entrega.

Após baixar arquivo e checksum na release, valide e carregue:

```sh
sha256sum -c xmqr-broker-0.11.2-linux-amd64.tar.gz.sha256
docker load -i xmqr-broker-0.11.2-linux-amd64.tar.gz
```

Secrets são externos e devem ser legíveis por UID10001, com chave/bundle/senha
0600 e diretório acessível. SAN precisa corresponder ao nome usado para conectar.
No teste a rede usa hostbroker com SAN DNS:broker. Não colocar chaves/estado
na imagem. Configure arquivos próprios antes de iniciar; fixtures não são para uso.

Use --read-only --cap-drop=ALL --security-opt no-new-privileges no run. O volume
do broker precisa ser gravável por10001. SIGTERM faz shutdown coordenado; use
`docker stop --time 20 xmqr-broker` antes de atualizar. Conserve volume/configuração
e backup offline; rollback da imagem não equivale a garantia de compatibilidade
de qualquer formato futuro. Imagens desta etapa preservam o estado existente.

Validação entre containers: mTLS/QoS1, retained após restart, shutdown0, CA e
senha erradas recusadas. Versão/ID/labels/proveniência registrados. Rootfsread-only
e caps removidas aprovados. Sem HEALTHCHECK superficial ou monitor externo.

## Versão sem inicializar o broker

```sh
docker run --rm --read-only --cap-drop=ALL xmqr-broker:0.11.2 --version
```

Não requer volumes/env/certificados; saída `mqtt-broker 0.11.2`, exit0.
Esse comando executa a consulta; `docker pull` baixa imagem publicada no
registry. DockerHub permanece publicação manual do operador; os arquivos
da releaseGitHub podem ser usados comdockerload. Client mantém0.7.1.
