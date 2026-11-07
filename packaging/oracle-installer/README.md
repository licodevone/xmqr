# XMQR Oracle Installer 0.1.0-rc.1

Instalação experimental nova em Ubuntu26.04 amd64/x86_64 com systemd.
Broker/client0.43.0, bridge0.5.0 e admin independente0.11.0 são pacotes
oficiais separados; esta versão identifica a automação de instalação.

## Instalar

Transfira o ZIP da release por SCP para a VPS e extraia em um diretório novo.
Na pasta extraída:

```bash
sha256sum -c SHA256SUMS
bash -n install_oracle_x86.sh
bash install_oracle_x86.sh --version
sudo bash install_oracle_x86.sh SEU_IPV4_PUBLICO
```

Troque SEU_IPV4_PUBLICO pelo endereço real. O instalador verifica OS,
arquitetura, instalação nova, SHA/nome/versão dos .deb e a CLI real dos
programas antes de gerar credenciais. Configura mTLS/SAN, senha própria,
ACL mínima, monitor9090 e observador19080 em loopback. Os três serviços
são habilitados apenas após os testes finitos terminarem.

Sucesso: XMQR_INSTALL_PASS. A ausência desse marcador não é aceite.
Se falhar, preserve os arquivos e informe etapa/primeira linha de erro.

## Retomadas restritas

Para a falha antiga de comparação da bridge em install-packages:

```bash
sudo bash install_oracle_x86.sh --resume-packages SEU_IPV4_PUBLICO
```

Para falha em mqtt-smoke, com pacotes e configuração já presentes:

```bash
python3 verify_oracle_installer.py
sudo bash install_oracle_x86.sh --resume-mqtt SEU_IPV4_PUBLICO
```

As retomadas verificam checkpoint, integridade e estado; não são bypass para
uma instalação genérica. A retomada MQTT preserva certificados/senha/token,
bundle, configuração e estado. Logs de cada tentativa ficam em diretório
privado do checkpoint. Não apagar dados para forçar uma retomada.

## Painel por SSH

No seu computador, usando a sua chave e o endereço da VPS:

```text
ssh -i CAMINHO_DA_CHAVE -o ExitOnForwardFailure=yes -N -L 127.0.0.1:19080:127.0.0.1:19080 ubuntu@IP_DA_VPS
```

Abra http://127.0.0.1:19080. Obtenha o token apenas no terminal da VPS:

```bash
sudo cat /etc/xmqr-admin/access.token
```

O admin0.11.0 é observador autenticado; não inclui automaticamente console
MQTT e contas web de fontes posteriores. Client de teste usa só xmqr/health;
dispositivos precisam de identidade e ACL próprias. Não há bridge automática.

Firewall/VCN/SSH e cobrança não são alterados. Conectividade MQTT externa
exige regras específicas posteriores. Não publicar monitor/painel na internet.
Folhas TLS duram365dias; CA3650dias. Planeje renovação e backup privado da PKI.

## Validação e integridade

O manifesto identifica os arquivos e hashes e fixa os três pacotes oficiais.
SHA256SUMS protege a integridade do conteúdo; o checksum do ZIP está na release.
O verificador testa versões e argumentos na CLI real usando um arquivo de
senha inexistente para parar antes da rede. Esse teste não lê credenciais.

A publicação é condicionada à CI do mesmo commit em Ubuntu26, incluindo
instalação nova, retomada de install-packages e retomada de mqtt-smoke com
preservação de materiais privados. EVIDENCE.json registra esses cenários.
Uma release candidata é experimental, não certificação MQTT ou produção.
