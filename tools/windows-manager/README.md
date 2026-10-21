# XMQR Manager para Windows

Aplicativo Rust independente, binário `xmqr-manager.exe`, sem Cargo workspace e
sem dependência do código do broker, client ou admin. Requer Rust 1.90 ou mais
recente para compilar suas bibliotecas de interface (os produtos mantêm seu MSRV).

```powershell
cargo build --locked --release
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo fmt --all -- --check
```

Sem argumentos abre uma única bandeja por usuário, sem janela de console. O
instalador do gerenciador registra o início no login. Sair da bandeja mantém os
serviços. Sem produtos instalados, o processo continua acompanhando instalações
mas não apresenta ícone. Remova o pacote do gerenciador para remover o autostart.

## Inventário e estados

Consulta somente a visão de 64 bits de
`HKLM\SOFTWARE\XMQR\Components\<id>` (máximo 64 componentes). O instalador
protege a escrita desse registro. Todos os valores são strings:

| Valor | Contrato |
| --- | --- |
| Kind | `broker`, `client` ou `admin` |
| DisplayName | Nome exibido, até 120 bytes, sem controles |
| Executable | Caminho absoluto local do executável instalado |
| ServiceName | Opcional: `xmqr-broker`, `xmqr-admin`, `xmqr-client-<instância>` |
| ConfigFile | Opcional: caminho absoluto do arquivo usado pelo serviço |
| CertificatesDir | Opcional: pasta absoluta dos certificados |
| LogsDir | Opcional: pasta absoluta dos logs |
| PanelUrl | Opcional: `http://127.0.0.1:PORTA` ou `http://[::1]:PORTA` |

Ausência do executável remove o componente do menu. Acesso negado não significa
ausência: aparece estado indisponível. Registros inválidos produzem diagnóstico.
Não são usados PATH, descoberta de processos por nome ou dados do painel web para
inferir instalação. Sem ServiceName, o componente aparece como CLI instalada e
não recebe comandos de serviço. Caminhos UNC/relativos e URLs remotas são recusados.

Verde: todos os serviços registrados estão em execução. Cinza: todos parados ou
somente CLI instalada. Amarelo: estados mistos, transição ou operação em andamento.
Vermelho: falha ou consulta indisponível. Cada componente também mostra texto.
**Verde não confirma conexão ou prontidão MQTT.** A consulta é repetida após cada
operação e periodicamente; a bandeja reflete alterações feitas em Services.msc.

## Controles e atalhos

Iniciar/parar/reiniciar usam ServiceController do Windows via PowerShell local;
reiniciar aguarda a parada antes de iniciar, com prazo total de 30 segundos.
Uma operação por vez; a interface permanece responsiva. Dependentes ativos
impedem a parada; não há encerramento forçado de processo. O helper verifica se o
executável configurado no SCM corresponde ao executável registrado pelo produto.

Ao receber acesso negado após clique explícito, é solicitada elevação UAC apenas
para o helper `--control start|stop|restart ID`. Ele relê o inventário HKLM e valida
nome e executável. Cancelar a elevação exibe erro e mantém os serviços. Não são
alteradas ACLs pelo gerenciador. Scripts são fixos e parâmetros são dados do
ambiente; nenhum conteúdo de configuração é avaliado como PowerShell.

Configuração abre no Bloco de Notas; pastas abrem no Explorer. O gerenciador não
lê certificados/chaves nem eleva o editor; permissões NTFS continuam valendo.
Editar não reinicia o serviço automaticamente. URLs do admin abrem no navegador.
Atalhos usam os caminhos registrados pelo instalador, inclusive instalações
personalizadas. Arquivo/pasta ausente apresenta erro, sem criar substitutos.

`--diagnose` retorna JSON com componentes, estados e diagnóstico (pode ser
capturado por processo pai com stdout redirecionado); `--version` e `--help`
também são suportados. Não mostra segredos, conteúdo de configuração ou payloads.

## Limites de aceite

Este programa não implementa persistência/ACL nativas dos produtos. As recusas
Windows existentes no broker/admin continuam visíveis como falhas. Build do
gerenciador não homologa a execução desses serviços. Testes de UAC, mudança real
de estado de serviço, reboot/login, DPI/temas, instalação/upgrade/desinstalação e
integração de todos os componentes precisam de uma VM Windows apropriada.

Dependências possuem licenças próprias; o pacote usa MIT e não as relicencia.
Consulte `third-party-licenses.md` e preserve LICENSE/NOTICE na distribuição.
