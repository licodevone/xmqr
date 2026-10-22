# P252 — Manager X e console Windows

Data: 2026-10-22. Base Broker 0fbe2dec; alterações locais anteriores preservadas.
Escopo autorizado: ícone X maior, verde/apagado, e Client do console web.
Trabalho paralelo: UI Manager, Admin A28, atualizadores, integração isolada;
integração e empacotamento pelo agente principal. Sem commit/push/tag/MSI.

## Resultado

Imagem X gerada a partir da referência, transparente, sem texto ou badge.
Conversão de empacotamento via System.Drawing: crop alfa, ocupação94%, ICO de
9 tamanhos, RGBA32. Fonte PNG preservada. Conversor geral encaminha Manager ao
conversor X para não sobrescrever os assets com o desenho anterior.

Manager mantém estados/modelo/ações, pinta somente a silhueta: verde todos os
serviços instalados Running; outros estados cinza com alfa reduzido. Sem
instalados continua oculto. Ícones Manager/Admin ligados nativamente ao PE,
sem alteração de recursos depois do link. build-windows.ps1 usa cópia e
auditoria somente leitura para Client/Admin/Manager.

Admin A28 recebe configuração explícita de console no TOML do serviço; a
ausência da seção mantém o comportamento anterior. Perfis mTLS apontam para
credenciais existentes; IDs próprios e processos separados do Client serviço.
Ver registro A28 e registro P252-manager-symbol-rendering para gates detalhados.

## Evidência

- Manager: fmt, Clippy estrito, 13 testes release, build Windows, --version PASS.
- Admin: fmt, Clippy estrito, 36 testes Windows, release/capabilities PASS.
- ICO nos dois executáveis: 9 imagens/10 recursos; hashes inalterados PASS.
- Integração real isolada: 9 verificações PASS, incluindo cookie/CSRF, negativos
  de autenticação/CSRF, conexão SUB mTLS QoS1, PUB e recebimento do marcador,
  desconexão e encerramento cooperativo dos filhos próprios com exit0.
- Contratos de empacotamento: 16 PASS, 1 NOT_RUN (fixture WiX opt-in), sem MSI.
- Inventário Admin CLI: BLOCKED offline por cc1.8.0 ausente; sem dependências
  ou locks novos, avisos existentes P246 reaproveitados.

SHA256 Manager: 2ee8cb3ea1b914724896fa91edf42b813e51a8d3509deafb05a5f5abd086ba2d.
SHA256 Admin: 42687cfe339a593fa8b0fff479bc833322ce2da1dea0d5160735aaaae0b4a8bc.

Sem acesso aos segredos instalados, alteração do SCM, ACL instalada ou conta
web nesta execução. Ferramentas sem token administrativo. Atualização no host
e aceitação visual dependem dos scripts pelo operador. O tamanho físico da
bandeja continua determinado pelo Windows e verde não atesta saúde MQTT.

Atualizadores: ver registro específico da entrega para provas e limites de
preservação de ACL herdada/identidade SYSTEM. Nenhum teste de helper significa
que a atualização administrativa instalada já foi executada.

## Entrega dos atualizadores

51 verificações isoladas PASS: parsing, CreateNew, hashes de substituição e
rollback, recusa de destinos/backup preexistentes, TOML conhecido e negativos,
ACL privada com LS RX obrigatório, caso herdado exato P250, File.Replace real
preservando owner/grupo/DACL herdada em fixture do operador, guardas Manager
aberto/arquivo em uso. Interop temporário SeRestorePrivilege compila; falha de
aquisição injetada comprovou nenhum Stop antes de mutação. Staging usa owner e
grupo originais, privilégios anteriores restaurados em Dispose/finally.

Limite: criação real com proprietário SYSTEM e token elevado não executada
neste ambiente; script verifica identidade e política e recusa divergências.
Nenhuma elevação, alteração de política global ou ACL instalada foi executada.
A entrega foi preparada para aplicação pelo operador com PowerShell elevado.
Diff-check dos arquivos novos/fatia fonte PASS pelos agentes. Diff-check global
Broker encontrou blank line at EOF anterior em docs/chat/2026-10-21.md; trabalho
anterior preservado, sem correção fora do escopo.

## Fechamento

Após revisão do guard de binários ProgramFiles, aceita TrustedInstaller SID
exato e CREATOROWNER InheritOnly restrito a diretório, sem permitir escrita
por usuários comuns; cobre GenericWrite/GenericAll. Helpers finais: 56 PASS.
Revisão independente somente leitura: ACLs reais de Manager/Admin (pasta e
exe) e Client exe PASS; Registry e ImagePath/LocalService compatíveis. Nenhuma
nova leitura de conteúdo privado ProgramData. Guide local e ZIP com CRC e
checksums individuais verificados; sem segredos ou configurações instaladas.
