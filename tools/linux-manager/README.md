# XMQR Manager — Ubuntu

Aplicativo de desktop independente, versão inicial 0.1.0, Python 3.10+/GTK 3.
Janela e bandeja opcional Ayatana AppIndicator; sem suporte à bandeja, a janela
continua disponível pelo menu de aplicativos. Requer sessão gráfica Ubuntu GNOME
com agente polkit. Não executar com sudo/root. Não depende de um servidor web
do Manager nem modifica os serviços ao abrir ou fechar.

## Instalar e usar

Construa em Ubuntu com Python3 e dpkg-deb:

```sh
python3 tools/linux-manager/build_deb.py --output dist/manager-ubuntu
sudo apt install ./dist/manager-ubuntu/xmqr-manager_0.1.0-1_all.deb
xmqr-manager
xmqr-manager --diagnose
```

O pacote declara GTK, GIO/GVfs, Nautilus, editor de texto e polkit como
dependências. AppIndicator é recomendado. O atalho aparece em Aplicativos e
inicia no login; para desabilitar o início automático, copie o arquivo de
`/etc/xdg/autostart/xmqr-manager.desktop` para `~/.config/autostart/` e defina
`Hidden=true`. Fechar a janela com bandeja ativa mantém o Manager; Sair mantém
os serviços. Sem bandeja, fechar a janela encerra apenas o Manager.

Selecione um componente para iniciar, parar, reiniciar ou abrir seus destinos.
Os controles dependem do estado observado e conferem novamente instalação,
unit e executável antes da operação. O systemd solicita autorização pelo polkit;
nenhuma regra de acesso irrestrito é instalada. Uma operação por vez, consulta
periódica a cada cinco segundos e mensagens de erro visíveis.

Os botões **Iniciar todos**, **Parar todos** e **Reiniciar todos** aparecem na
janela e na bandeja. Incluem somente serviços XMQR configurados, ignorando CLIs
sem unit. O início segue broker, admin, clients; a parada segue a ordem inversa.
Reiniciar todos para primeiro o conjunto inteiro e depois inicia todos,
inclusive os serviços inicialmente parados. Estado indisponível ou transição
bloqueia o conjunto antes da primeira alteração. Erro interrompe as etapas
seguintes, informa a quantidade concluída e atualiza os estados. Não há
transação nem rollback automático; a política polkit pode solicitar autorização
por unit. Não é instalada uma política que dispense autenticação.

Configurações editáveis e pastas acessíveis usam os aplicativos do desktop.
Destinos protegidos usam o backend GVfs `admin:///`, com autenticação, sem
mudar permissões. O editor deve suportar URIs GIO, como gnome-text-editor.
O Manager consulta o tipo do destino antes de abrir, distingue erro/ausência
e não cria um arquivo substituto. A abertura da aplicação externa não comprova
que o usuário concluiu a edição. A consulta de logs de serviço usa journalctl,
últimas 300 entradas, sem pager e com autenticação via pkexec; exibe somente
na janela local. Não salva conteúdo de configuração, chaves ou logs em evidências.

## Inventário compatível com os pacotes existentes

Broker: `/usr/bin/mqtt-broker`, unit `xmqr-broker.service`, configuração inicial
`/etc/xmqr/broker.env`. O pacote atual usa EnvironmentFile; não assumir que um
TOML de exemplo foi ativado. Certificados podem ser provisionados em outro
diretório; registre esse caminho explicitamente quando aplicável.

Client: `/usr/bin/mqtt-client`; descobre units carregadas ou habilitadas
`xmqr-client-sub@INSTANCIA.service`, `xmqr-client-pub@INSTANCIA.service` e
`xmqr-client-bridge@INSTANCIA.service`. Configurações pub/sub usam
`/etc/xmqr-client/INSTANCIA.conf` e certificados na subpasta `INSTANCIA`.
Bridge usa `/usr/bin/mqtt-bridge` e `bridge-INSTANCIA.toml`. O modelo de unit
sem instância não vira serviço fictício. Instâncias configuradas mas nunca
carregadas/habilitadas devem ser cadastradas no inventário protegido abaixo.

Admin: o pacote publicado instala `/usr/bin/xmqr-admin`, sem unit systemd e sem
painel ativo por padrão. Aparece como CLI instalada quando não há unit.
Uma unit `xmqr-admin.service` existente é descoberta automaticamente; cadastre
configuração e URL reais para habilitar os atalhos correspondentes.
O Manager não fabrica token, credenciais ou endpoint. A URL deve ser
HTTP loopback com porta explícita; sua presença não comprova disponibilidade.

## Caminhos personalizados e serviços provisionados

Crie arquivos JSON em `/etc/xmqr-manager/components.d/`, proprietário root,
modo 0644 ou mais restrito; diretórios root sem escrita para grupo/outros.
Não coloque senhas ou tokens nesses registros. Até 64 componentes e 16 KiB
por arquivo; nenhum symlink no inventário. Exemplo com os campos disponíveis:

```json
{
  "id": "admin",
  "kind": "admin",
  "name": "XMQR Admin",
  "executable": "/usr/bin/xmqr-admin",
  "service": "xmqr-admin.service",
  "config": "/etc/xmqr-admin/admin.env",
  "config_dir": "/etc/xmqr-admin",
  "certificates": null,
  "logs": null,
  "panel": "http://127.0.0.1:9080/"
}
```

O exemplo pressupõe esse serviço previamente provisionado. Adapte os caminhos
ao comando realmente usado pelo serviço. O mesmo ID substitui a descoberta
padrão. O executável precisa estar instalado e corresponder ao ExecStart da
unit. Serviços de outros produtos, caminhos relativos, travessias `..` e URLs
remotas são recusados. Não são aceitos wrappers shell para ExecStart: registre
o binário real ou adapte a unit de forma administrativa. Nomes de instância
aceitam letras ASCII, números, `_` e `-`, até 64 caracteres.

## Validação e limites

```sh
python3 -m unittest discover -s tools/linux-manager/tests -v
dbus-run-session -- xvfb-run -a python3 tools/linux-manager/tests/gui_smoke.py
desktop-file-validate tools/linux-manager/xmqr-manager.desktop
```

O smoke usa serviços simulados, nunca os serviços do operador. Testes de GUI
isolados não homologam autenticação polkit, GVfs admin, login, Wayland e interação
real com os três serviços. Consulte o registro P255 para o que foi executado.
Ubuntu Server sem desktop pode usar `--diagnose` quando systemd estiver ativo;
para uso normal mantenha as CLIs existentes. Licença MIT do código próprio;
Python, GTK/GNOME e bibliotecas do sistema mantêm suas respectivas licenças.
