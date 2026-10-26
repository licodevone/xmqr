# P254 — Diagnóstico dos atalhos do Manager

Data: 2026-10-25, America/Sao_Paulo. Prompt: [P254 v1.0](../broker/254-manager-shortcuts-diagnosis.md).
Pedido: verificar as opções de configuração e pastas dos componentes broker,
client e admin mostradas no menu do XMQR Manager.

## Estado verificado

- Broker HEAD `654410c`; mudanças anteriores em docs/chat preservadas.
- Sessão Windows sem elevação. Manager instalado em
  `C:\Program Files\XMQR\Manager\xmqr-manager.exe`.
- SHA-256 instalado:
  `2EE8CB3EA1B914724896FA91EDF42B813E51A8D3509DEAFB05A5F5ABD086BA2D`.
  Coincide com o artefato documentado em
  [P252](P252-manager-symbol-rendering.md), sem novo build nesta análise.
- `--diagnose` do executável instalado: saída 0, inventário sem erro, admin,
  broker e client-default declarados em execução segundo o Windows.
- Notepad, Explorer e Windows PowerShell existem nos caminhos que o código usa.
- GET não autenticado de `http://127.0.0.1:9080/`: HTTP 200.
  Isso verifica a página inicial, sem comprovar login ou operação MQTT.

## Sondagens nativas somente leitura

Destinos obtidos de `HKLM\SOFTWARE\XMQR\Components`, visão 64 bits.
Foi consultado `File.GetAttributes` e tentada abertura de arquivo para leitura,
fechando o handle sem ler bytes. Para pastas foi tentado o primeiro passo de
enumeração, descartando os nomes. Não foi aberto conteúdo de configuração,
certificados, chaves ou logs.

| Componente | Opção | Destino abaixo de C:\ProgramData\XMQR | Resultado de acesso |
| --- | --- | --- | --- |
| admin | Configuração | admin\admin.toml | UnauthorizedAccessException |
| admin | Pasta de configurações | admin | UnauthorizedAccessException |
| admin | Certificados | admin\certificates | UnauthorizedAccessException |
| admin | Logs | admin\logs | UnauthorizedAccessException |
| broker | Configuração | broker\broker.toml | Permitido |
| broker | Pasta de configurações | broker | Permitido |
| broker | Certificados | broker\certificates | Permitido |
| broker | Logs | broker\logs | UnauthorizedAccessException |
| client-default | Configuração | client-default\client.toml | UnauthorizedAccessException |
| client-default | Pasta de configurações | client-default | UnauthorizedAccessException |
| client-default | Certificados | client-default\certificates | UnauthorizedAccessException |
| client-default | Logs | client-default\logs | UnauthorizedAccessException |

Metadados das pastas raiz admin/client e de broker/logs podem ser consultados,
apesar da recusa de enumeração. A checagem `fs::metadata` sozinha não detecta
esse caso. Nos arquivos/certificados/logs internos de admin e client, o acesso
aos próprios metadados já falha. A recusa não demonstra inexistência do destino.

A leitura de ACL disponível no broker confirmou grant FullControl explícito
para o usuário da sessão na raiz, em broker.toml e em certificates. ACLs das
pastas protegidas admin/client/logs não ficaram disponíveis para esta sessão;
não se afirma qual ACE exata causa a recusa nesses destinos.

## Causa e comportamento do código

Em [platform.rs](../../tools/windows-manager/src/platform.rs), `shortcut` relê o
inventário e consulta metadados. Configuração é lançada no Notepad; pastas são
passadas ao Explorer, usando o token atual. Os atalhos não têm o fluxo UAC dos
controles de serviço. O contrato está explícito no
[README do Manager](../../tools/windows-manager/README.md).

Em [ui.rs](../../tools/windows-manager/src/ui.rs), as opções são adicionadas
quando o caminho está cadastrado (`is_some`), sem verificar acesso. O erro do
worker é guardado em `app.message` e aparece como texto no menu principal. Não
há aviso independente da bandeja. Para pastas cujo metadata passa, o Manager
considera o `spawn` do Explorer suficiente e não confirma navegação ou listagem.
Por isso uma operação pode terminar como concluída apesar da pasta protegida.

Conclusão comprovada: a política de acesso da sessão impede nove dos doze
destinos locais. O fluxo do Manager não resolve nem explica adequadamente esse
acesso. Não há evidência de que os caminhos tenham ficado antigos após a mudança
da pasta do projeto: todos apontam para ProgramData, e a configuração/pastas
permitidas do broker foram acessadas com sucesso nas sondagens.

## Limites, decisão e próxima alteração

- A automação de janelas não expôs a bandeja nem uma janela do Manager; não foi
  possível reproduzir os cliques por essa interface. Nenhuma janela de editor
  ou Explorer foi aberta pelo agente para ler dados privados.
- A falha de abertura visual dos três destinos permitidos do broker não está
  reproduzida. Não atribuir esses três casos às permissões sem prova adicional.
- Correção indicada: tornar a recusa de acesso visível e específica, distinguir
  acesso negado de destino ausente, verificar o acesso necessário ao destino e
  definir um fluxo administrativo explícito para recursos protegidos. Isso não
  equivale a liberar ACLs amplamente nem a afirmar que elevar Explorer resolve
  o problema. Requer implementação/testes e validação UAC próprios.
- Nenhuma mudança no código, instalação, permissões, versão ou serviços foi
  aplicada. Gates Rust/interoperabilidade não se aplicam à análise documental.
- Uma tentativa posterior de persistir evidência JSON com comando composto foi
  recusada pela política da ferramenta antes da execução; este registro contém
  o resumo das sondagens anteriores bem-sucedidas, sem depender desse comando.

Entrega: prompt e este diagnóstico, mais histórico da conversa. Sem commit,
push, tags ou publicação.

Verificação documental: `git diff --check` retornou 0; houve apenas aviso de
normalização LF/CRLF no histórico anterior já modificado, que foi preservado.

## Revalidação v1.1 — sessão administrativa em 2026-10-25

O token desta sessão foi verificado como elevado (`IsInRole(Administrator)`
verdadeiro). Os 12 destinos registrados permitiram abertura para leitura de
arquivo ou primeiro passo de enumeração de pasta, sem leitura de bytes ou
registro dos nomes enumerados. Isso não invalida a sondagem anterior sem
elevação nem comprova funcionamento dos atalhos no processo normal do Manager.

O inventário continua apontando para ProgramData, com os mesmos três
componentes. O hash instalado continua
`2EE8CB3EA1B914724896FA91EDF42B813E51A8D3509DEAFB05A5F5ABD086BA2D`.
Get-Service indicou Running para xmqr-admin, xmqr-broker e
xmqr-client-default. HEAD HTTP da raiz do painel retornou 200; não houve login
ou teste MQTT nesta revalidação. --diagnose não foi repetido com sucesso aqui.

ACLs foram consultadas com o token elevado: raízes admin/client-default e
broker/logs têm grants para SYSTEM, Administrators e outra identidade. Broker,
broker.toml e broker/certificates também têm grant direto FullControl para o
usuário atual, ausente nos três primeiros destinos inspecionados. Identidades
pessoais não foram registradas. Não se calculou acesso efetivo de todos os
grupos de um token sem elevação; os resultados negativos anteriores permanecem
a evidência direta desse caso. Nenhuma ACL foi alterada. A política restritiva
também está documentada em packaging/windows/README.md.

A revisão atual de platform.rs e ui.rs mantém a conclusão: atalhos usam o token
atual, metadata não comprova listagem e o resultado só atualiza texto do menu.
A skill computer-use foi usada para listar janelas; não retornou janela do
Manager ou da bandeja. Não se lançou uma segunda instância nem se reproduziram
cliques. A abertura visual dos três destinos permitidos do broker permanece
sem diagnóstico conclusivo.

Uma chamada composta de diagnóstico foi recusada pela revisão automática antes
da execução. A verificação foi concluída por chamadas menores somente leitura;
não houve tentativa de elevação ou de alteração da política. Documentação e
históricos são as únicas mudanças desta retomada; sem build, instalação,
serviços alterados, publicação ou mudança de versão.
