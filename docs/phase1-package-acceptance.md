# Aceite de pacote da fase 1

Checkpoint P61: lifecycle aprovado em Ubuntu26amd64, com broker0.11.0/client0.7.0,
upgrade desde0.10.0/0.5.0 e rollback. O harness inclui docsXMQR explicitamente
na imagemDocker mínima, que os exclui por padrão. [Evidência final](../prompts/registros/P61-aceite-final-fase1.md).
O contrato abaixo permanece reproduzível. Builds do runner ficam em /tmp nativo;
logs e snapshots no workspace. --build-cache-root pode reusar apenas a pasta
/tmp/xmqr-phase1-build-* existente, sem pular nenhum gateCargo.

O gate de distribuição é separado do aceite de quotas/recuperação MQTT. O
harness [test_package.sh](../packaging/test_package.sh) cobre broker e client
em um container descartável Ubuntu 26.04 amd64: install, upgrade, rollback,
remove e purge. Não executa serviços, TLS ou recuperação do WAL.

## Entradas e execução

Construa os pacotes candidatos com scripts/build_deb.py em Ubuntu 26.04 amd64,
na árvore exata validada. Identifique os pacotes antigos publicados e seus
SHA-256, mantendo os quatro arquivos separados e sem alterar tags antigas.
A versão Debian candidata deve ser maior para cada pacote; repetir a mesma
versão não testa upgrade. Defina nomes exatos nos argumentos, sem globs.

Com Docker já disponível, coloque os quatro pacotes em uma pasta de artefatos
com os nomes abaixo e execute no checkout broker:

~~~sh
docker run --rm --platform linux/amd64 \
  -e XMQR_DISPOSABLE_PACKAGE_TEST=1 \
  -v "$PWD:/source:ro" -v "/caminho/artefatos:/artifacts:ro" \
  ubuntu:26.04 sh /source/packaging/test_package.sh \
  /artifacts/old-broker.deb /artifacts/old-client.deb \
  /artifacts/new-broker.deb /artifacts/new-client.deb
~~~

Os nomes acima podem ser substituídos pelos nomes reais dos arquivos, sem
renomear o conteúdo do pacote. A imagem Ubuntu requer resolução APT/acesso de
rede e dependências dos pacotes. O script instala somente dentro do container,
recusa host sem /.dockerenv, conta não root, plataforma divergente ou pacotes
já instalados. Não executar em container com dados do operador. O bind mount
da fonte e dos pacotes é somente leitura; não montar /etc ou /var/lib do host.

## Evidência exigida

O script imprime SHA-256 dos quatro artefatos e versões/status dpkg por etapa.
Exige upgrade crescente, faz downgrade explícito e verifica conteúdo do
conffile editado, arquivo fictício de estado e credencial fictícia por SHA-256.
Também confere units, ausência de habilitação automática, contas de serviço,
modo privado do estado e preservação de dados após remove/purge.

A linha PACKAGE_LIFECYCLE_PASS só aparece após todos os checks. Salve o log,
exit code, hashes, versões e imagem/arquitetura no registro do marco. Esse PASS
comprova ciclo de pacotes e arquivos de operador; o arquivo fictício não prova
compatibilidade ou replay de estado MQTT, que deve ser aprovado por P55/Unix.
Sem Linux ou os quatro pacotes nativos, marque BLOCKED. Não concluir a fase 1
nem criar tag de aceite com base apenas na sintaxe do harness.

O script verifica units instaladas com systemd-analyze; execução real de
start/stop/reload/shutdown exige o gate existente scripts/verify_systemd.py em
um ambiente systemd apropriado e isolado.

Resultados desta preparação: [registro P59](../prompts/registros/P59-aceite-pacotes.md).

## Runner dos gates de código no WSL do operador

O runner do broker usa checkout e estado temporário, sem sudo, APT ou systemctl.
No Ubuntu26 acessível à conta do operador, a partir da pasta agregadora:

~~~sh
python3 -B xmqr/scripts/verify_phase1.py --client-root xmqr-client
~~~

Ele registra versões Rust, HEAD/status dos dois repositórios, formatação, testes,
Clippy, build, inventário e integrações P54/P55/Will/C27/C38/Mosquitto open-lab. Os binários vêm dos
fontes desta execução, em target/phase1-*/{broker,client}-target; não usa os
softwares instalados. TMPDIR é /tmp nativo para estado/permissões das fixtures.
Os comandos Cargo usam cache offline: cache ou toolchain ausente exige resolver
o pré-requisito e repetir; o runner não instala nada. C27 requer openssl.

O caminho de logs e summary.json é impresso. Mesmo UNIT_INTEGRATION_PASS não
comprova PACKAGE_LIFECYCLE_PASS nem fecha a fase 1 sozinho. Compartilhe o resumo
e os logs que falharam para análise; não compartilhar credenciais ou estado real.

O runner grava sources-before.json e sources-after.json com HEAD e hashes dos
arquivos Git versionados/novos não ignorados. Qualquer alteração durante gates
invalida evidência. Summary mantém phase1_accepted=false e saída PHASE1_BLOCKED
até o aceite de pacote e interop externa pertinente terem resultado real.

Revisão P59 2.3: o runner também executa interop independente Mosquitto
open-lab se mosquitto_pub, mosquitto_sub e stdbuf já estiverem disponíveis.
Se faltar ferramenta, external_interop no resumo registra BLOCKED específico;
o runner não instala nada. O status desse gate não comprova TLS/mTLS/ACL externa
e não substitui o ciclo de pacote separado.

## Material TOML P52 no pacote candidato

O broker candidato inclui /usr/share/doc/xmqr-broker/broker.toml.example e
configuration.md. São exemplo e guia opt-in: a instalação preserva broker.env
e não ativa MQTT_CONFIG automaticamente. O harness exige ambos no artefato
candidato antes do APT e compara os arquivos instalados com o conteúdo do
pacote. Após rollback, exige os arquivos exatamente conforme o pacote antigo,
ou ausência quando a versão antiga não os distribuía. Conteúdo editado de
conffile e estado/credencial fictícios continua protegido pelos checks de hash.
