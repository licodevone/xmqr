# Instalar XMQR na Oracle pelo terminal

P260 v1.7. Destino informado: `163.176.255.19`, hostname `xmqr`.
O operador confirmou Ubuntu26.04.1/x86_64 pela saída da própria sessão SSH.
Este guia não é uma declaração de instalação concluída.

O [instalador](../scripts/install_oracle_x86.sh) usa os pacotes publicados
broker0.43.0, client0.43.0/bridge0.5.0 e admin independente0.11.0.
Ele confere os três SHA-256 antes de instalar, gera certificados próprios,
senha MQTT e token web privados, configura systemd e executa probes finitos.
O client instalado como serviço é um assinante de teste de `xmqr/health`.
O admin publicado é observador autenticado, sem console MQTT/contas web
dos incrementos posteriores presentes apenas nas fontes locais.

## 1. Copiar o instalador pelo Windows

Mantenha o terminal Ubuntu aberto. Em uma segunda janela PowerShell, execute:

```powershell
scp -i "$env:USERPROFILE\ssh-key-2026-11-03.key" "D:\projects\my-project\acmebr-projects\xmqr.acmebr\xmqr\scripts\install_oracle_x86.sh" ubuntu@163.176.255.19:/home/ubuntu/install_oracle_x86.sh
```

Use a mesma chave que funcionou no SSH. O comando transfere somente o script;
a chave privada continua no Windows. SSH/SCP mantêm validação da chave do host.

## 2. Validar e executar no Ubuntu

Na sessão `ubuntu@xmqr`, execute:

```bash
bash -n "$HOME/install_oracle_x86.sh" && sudo bash "$HOME/install_oracle_x86.sh" 163.176.255.19
```

`bash -n` analisa o arquivo sem instalar. Se falhar, o comando sudo não será
executado. O script aceita somente instalação nova em Ubuntu26 amd64 com
systemd e recusa configuração/estado/contas/portas já utilizados pelo XMQR.
Não faz atualização nem remoção de instalação anterior.

O APT instala dependências dos repositórios Ubuntu e os três pacotes oficiais
do GitHub. O script gera CA privada em `/root/xmqr-oracle-pki`, folhas de
servidor/cliente e SAN para o IP informado, localhost, 127.0.0.1 e xmqr.
Não há senha padrão. O bundle exige certificado cliente, senha e ACL mínima.

O script para e desabilita somente os serviços novos sob seu controle se
falhar, preservando arquivos para diagnóstico. Não apague configuração nem
repita o instalador sobre uma execução parcial.

## 3. Conferir o resultado

O sucesso completo deve terminar com:

```text
XMQR_INSTALL_PASS
mqtt-broker 0.43.0
mqtt-client 0.43.0
mqtt-bridge 0.5.0 (xmqr-client 0.43.0)
xmqr-admin 0.11.0
```

Esse marcador só é emitido após readiness, pub/sub mTLS QoS1, retained após
reinício do broker, senha inválida recusada, API web autenticada, recusa sem
token e três serviços ativos. É um smoke test experimental, não certificação
integral MQTT, teste de perda de energia ou homologação de produção.

### Retomar a falha conhecida de conferência da bridge

A primeira revisão comparava a saída da bridge com uma string incompleta.
Quando a falha foi `Versao inesperada da bridge` na etapa install-packages,
os pacotes já estão instalados; certificados/configuração ainda não foram
criados. Não executar a instalação nova nem apagar diretórios.

Copie novamente o arquivo corrigido com o comando SCP do passo1. No Ubuntu:

```bash
mqtt-bridge --version
bash -n "$HOME/install_oracle_x86.sh" && sudo bash "$HOME/install_oracle_x86.sh" --resume-packages 163.176.255.19
```

A versão esperada é `mqtt-bridge 0.5.0 (xmqr-client 0.43.0)`.
A retomada aceita somente o checkpoint privado de falha install-packages,
confere os pacotes instalados por versão e dpkg-V, os hashes do cache e a
ausência de estado/credenciais/configuração nova. Reutiliza os pacotes sem
APT/reinstalação, preserva o status anterior e segue para preparar mTLS.
Estado/arquivo divergente ou segunda retomada é recusada para revisão.

Execute também:

```bash
sudo systemctl --no-pager --full status xmqr-broker.service xmqr-client-sub@oracle.service xmqr-admin.service
curl --fail http://127.0.0.1:9090/ready
sudo cat /var/lib/xmqr-oracle-install/status
```

Os serviços ficam habilitados para iniciar com o Ubuntu. O cliente recebe
apenas o tópico sintético de teste, não os tópicos dos dispositivos existentes.

## 4. Abrir o painel no Windows

Em uma janela PowerShell, execute e mantenha o processo aberto:

```powershell
ssh -i "$env:USERPROFILE\ssh-key-2026-11-03.key" -o ExitOnForwardFailure=yes -N -L 127.0.0.1:19080:127.0.0.1:19080 ubuntu@163.176.255.19
```

Abra **http://127.0.0.1:19080** no navegador do Windows. O painel da VPS usa
19080 para poder coexistir com o admin Windows em9080. As portas iguais nas
duas pontas mantêm o contrato Host/Origin do painel.

Na sessão SSH Ubuntu, obtenha o token para inserir apenas na tela do painel:

```bash
sudo cat /etc/xmqr-admin/access.token
```

O token não é a senha MQTT. Não o envie em mensagens ou logs de diagnóstico.
O túnel precisa continuar aberto enquanto você usa o painel; Ctrl+C o encerra.

## 5. Diagnosticar uma falha

Envie o nome da etapa e a mensagem de erro. Estes comandos mostram estado e
logs dos serviços, sem ler arquivos privados de credenciais:

```bash
sudo cat /var/lib/xmqr-oracle-install/status
sudo journalctl -u xmqr-broker.service -u xmqr-client-sub@oracle.service -u xmqr-admin.service -n 60 --no-pager
```

Uma recusa anterior ao início pode não criar o arquivo status. Nesse caso,
copie a mensagem exibida no terminal. Não enviar server.key, client.key,
ca.key, password, security.toml ou access.token.

## Operação e acesso dos dispositivos

| Recurso | Endereço / caminho |
| --- | --- |
| MQTT mTLS | 0.0.0.0:8883 na VPS; IP/SAN 163.176.255.19 |
| Monitor | 127.0.0.1:9090, somente loopback |
| Observador web | 127.0.0.1:19080, somente loopback |
| Configuração broker | /etc/xmqr/broker.env |
| Bundle privado | /etc/xmqr/security.toml, xmqr, 0600 |
| Estado broker | /var/lib/xmqr, usuário xmqr |
| Identidade cliente de teste | /etc/xmqr-client/oracle, xmqr-client, 0700 |
| Senha cliente de teste | /etc/xmqr-client/oracle/password, xmqr-client, 0600 |
| Token observador | /etc/xmqr-admin/access.token, xmqr-admin, 0600 |
| PKI privada / CA | /root/xmqr-oracle-pki, root, 0700 |
| Status de instalação | /var/lib/xmqr-oracle-install/status |

O script não altera firewall do Ubuntu, regras OCI, SSH ou cobrança. Acesso
externo direto à8883 depende dessas regras e não é comprovado pelo smoke
local. Para um ESP32/cliente externo, criar identidade/certificado próprios
e concessões para seus tópicos; não reutilizar a identidade limitada de teste.
Nunca publicar o monitor9090 nem o painel19080 na internet.

As folhas TLS têm validade365 dias e a CA3650 dias: planejar renovação antes
do vencimento. Guardar backup privado da CA/configuração separadamente do
backup MQTT. Parar o broker antes de backup/restore do estado. Não inferir
custo zero pelo fato de o software ter sido instalado.

## Fontes e validação desta entrega

- [Release broker0.43.0](https://github.com/licodevone/xmqr/releases/tag/v0.43.0)
- [Release client0.43.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.43.0)
- [Release admin0.11.0](https://github.com/licodevone/xmqr-admin/releases/tag/v0.11.0)
- [Hashes e compatibilidade](current-releases-wsl.md)
- [Registro de execução e limitações](../prompts/registros/P260-oracle-instance-install.md)

O agente conferiu metadados e digests dos três pacotes pela API GitHub e
revisou o script contra as fontes das tags. Os três blocos Python embutidos
passaram compilação sintática local. Bash local foi BLOCKED por falha de
inicialização/IPC do ambiente Windows antes da análise, por isso bash-n é
obrigatório no passo2. Nenhuma instalação, serviço, geração de credencial ou
campanha de integração desta entrega foi executada na VPS pelo agente.
