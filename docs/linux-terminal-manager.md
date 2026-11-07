# XMQR Manager Terminal 0.1.0-rc.1

Companheiro do Manager Ubuntu para SSH/Ubuntu Server com systemd. Python3.10+
e biblioteca padrao; nao precisa GTK, ambiente grafico ou agente polkit.
Reutiliza o backend do Manager desktop, sem alterar broker/client/admin.
Versao candidata: testes com systemd real ainda pendentes nesta entrega.

## Copiar para o servidor

No PowerShell, a partir da pasta raiz do agrupamento, adapte chave e host:

```powershell
scp -i CAMINHO_DA_CHAVE .\xmqr-manager-terminal-0.1.0-rc.1.zip .\xmqr-manager-terminal-0.1.0-rc.1.zip.sha256 ubuntu@IP_DA_INSTANCIA:/home/ubuntu/
```

Na instancia:

```bash
cd "$HOME" &&
sha256sum -c xmqr-manager-terminal-0.1.0-rc.1.zip.sha256 &&
pasta=$(mktemp -d "$HOME/xmqr-manager-terminal.XXXXXX") &&
python3 -m zipfile -e xmqr-manager-terminal-0.1.0-rc.1.zip "$pasta" &&
cd "$pasta" &&
sha256sum -c SHA256SUMS &&
python3 -I terminal.py --version &&
python3 -I terminal.py status
```

O ultimo comando e somente consulta. Devem aparecer broker/admin e o client
`client-sub-oracle` se instalados/carregados no perfil Oracle do instalador.
Client sem instancia tambem pode aparecer como CLI instalada; nao vira um
servico ficticio. Mais de uma instancia exige ID completo para controle.

## Instalar o comando opcional

Na pasta extraida e depois da verificacao acima, o bloco abaixo recusa
destinos existentes. O nome do Manager grafico permanece disponivel.

```bash
(
  set -eu
  destino=/usr/local/lib/xmqr-manager-terminal
  comando=/usr/local/bin/xmqr-manager-terminal
  if [ -e "$destino" ] || [ -L "$destino" ] || [ -e "$comando" ] || [ -L "$comando" ]; then
    printf '%s\n' 'Manager Terminal ja existe; revise a instalacao antes de substituir.' >&2
    exit 1
  fi
  sudo install -d -o root -g root -m 0755 "$destino"
  sudo install -o root -g root -m 0644 backend.py terminal.py "$destino/"
  sudo install -o root -g root -m 0755 xmqr-manager-terminal "$comando"
)
```

O launcher usa Python isolado e arquivos root em diretorio proprio. Sem
instalar, `python3 -I terminal.py` abre o mesmo menu na pasta extraida.
Uma falha parcial de copia exige revisao dos destinos antes de nova tentativa.

## Usar pelo terminal

```bash
xmqr-manager-terminal status
sudo xmqr-manager-terminal
sudo xmqr-manager-terminal --dry-run restart all
sudo xmqr-manager-terminal restart all
sudo xmqr-manager-terminal stop client
sudo xmqr-manager-terminal start client
sudo xmqr-manager-terminal logs broker
xmqr-manager-terminal paths admin
```

Menu: Status, Iniciar, Parar, Reiniciar, Logs, Caminhos e Sair. Alvos: broker,
admin, client, all ou o ID completo mostrado em status. Se houver varios
clients, use o ID completo, por exemplo `client-sub-oracle`. Escolher parar ou
reiniciar interrompe as conexoes desses servicos. Acoes individuais respeitam
o estado: iniciar usa parado/falha; parar/reiniciar usa em execucao.

Operacoes gerais iniciam Broker/Admin/Clients e param na ordem inversa;
reiniciar geral primeiro para, depois inicia. Um erro interrompe a sequencia
e informa quantas etapas foram concluidas; nao promete rollback atomico.
Reconsulte status antes de repetir. --dry-run somente prepara o plano.

## Limites e seguranca

- Somente softwares instalados e units XMQR permitidas. ExecStart divergente,
  estado desconhecido/em transicao ou masked bloqueia controle. Ausencia de
  configuracao do client bloqueia o plano de inicio/reinicio antes de parar.
- Controle exige sudo/root explicitamente; nao modifica sudoers ou polkit.
  Logs dependem das permissoes do journal. Sem pkexec ou prompts graficos.
- Estado ativo e informacao systemd; nao garante readiness MQTT, rede Oracle
  ou entrega de mensagens aos dispositivos. O menu nao fica em background.
- Caminhos sao referencias do inventario, sem ler valores privados; nao ha
  editor de certificados/senhas. Journal e mostrado apenas no seu terminal,
  limitado a300entradas; nao compartilhe logs que contenham dados privados.
- Sem configuracao de firewall, atualizacao de pacote, criacao de servicos,
  tokens, credenciais ou acesso remoto automatico. O Manager nao iguala os
  paineis web: a Oracle ainda usa o admin publicado anterior ao Console MQTT.
- Reutiliza registros root protegidos em /etc/xmqr-manager/components.d,
  descritos em tools/linux-manager/README.md na fonte do projeto.

## Validacao

`python3 -m unittest discover -s tools/linux-manager/tests -v` na fonte.
Os testes novos simulam systemd e nao iniciam servicos reais. Evidencia e
limites em prompts/registros/P262-linux-terminal-manager.md na fonte.
Fonte MIT; dependencias do sistema mantem suas licencas.
