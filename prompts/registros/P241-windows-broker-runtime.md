# P241 - Broker nativo Windows: registro de execucao

Data: 2026-10-21. Prompt: [P241 v1.2](../broker/241-windows-broker-runtime.md).
Escopo autorizado: comecar pelo broker, com agentes em paralelo. Sem alteracao
de versao, commit, push, release ou instalacao no host. AGENTS.md, docs/chat e
P240 modificados pelo operador foram preservados.

## Resultado funcional

Resumo estruturado com hashes de fonte e executaveis:
[p241-windows-broker-runtime-20261021.json](../../docs/results/p241-windows-broker-runtime-20261021.json).

O broker agora inicializa estado e executa MQTT no Windows nativo. A publicacao
de WAL novo usa arquivo temporario no mesmo diretorio, write-through, sync_all,
fechamento e move_atomic sem overwrite. Snapshots usam replace_atomic depois
de sync_all/fechamento; o WAL so e compactado depois do sucesso. O wrapper seguro
de atomicwrites 0.4.4 usa MoveFileExW com WRITE_THROUGH, sem COPY_ALLOWED.
Nao ha codigo unsafe proprio. O fsync de diretorio Unix foi preservado.

Limpeza de temporarios ocorre sob bloqueio exclusivo; state.wal.init nunca e
reproduzido como estado. Contencao Windows e reconhecida pelo codigo fs2 nativo.
Formato WAL/snapshot/MQTT nao mudou. Backup/restauracao do admin legado continua
fora do escopo Windows; nao foi criado fallback vazio de sincronizacao.

SCM: pedido de parada durante inicializacao percorre o encerramento duravel;
status inicial e handler sao serializados; falha ao publicar Running fecha
listeners e drena ator antes de retornar erro. Console aceita Ctrl+Break e
Ctrl+C; SCM usa exclusivamente seu sinal cooperativo.

## Validacao executada

Ambiente nativo Windows x64 MSVC. CARGO_HOME curto permitido:
`C:\Users\licod\AppData\Local\Temp\xmqr-cargo`. TMP/TEMP dos testes em
`target/p241-temp`. Sem elevar, modificar ACL do host ou usar estado do operador.

| Verificacao | Resultado |
| --- | --- |
| Check nativo inicial do adaptador, antes da persistencia | PASS pelo agente SCM |
| Testes dirigidos de persistencia | 14 PASS, incluindo crash de inicializacao e bloqueio concorrente |
| Testes dirigidos de falhas de IO | 8 PASS; falha de publicacao nao autoriza truncar WAL |
| Suite completa da biblioteca experimental | 247 PASS / 0 FAIL / 1 ignorado preexistente |
| Caso preexistente ignorado, selecionado explicitamente com --ignored --exact | 1 PASS: Will saturado conserva obrigacao apos recuperacao |
| Testes do binario experimental | 13 PASS |
| Build debug do adaptador | PASS |
| Check CLI comum com lock raiz preservado | PASS |
| fmt raiz e manifest experimental | PASS |
| Clippy experimental all-targets -D warnings | FAIL: imports/dead-code Windows preexistentes em auth/dynamic e mqtt/router/mod; nenhuma supressao global adicionada |
| MQTT real debug | PASS: PUBACK QoS1 retido, parada normal, recuperacao apos reinicio e crash do processo |
| MQTT real release | PASS: os mesmos 3 cenarios no executavel usado para MSI |
| Get-Service xmqr-broker ao final | Servico inexistente; nao esta instalado |
| Entrada de servico release fora do SCM | Recusa correta com saida 1; nao inicia broker como se fosse servico |

O runner [verify_windows_broker_runtime.py](../../scripts/verify_windows_broker_runtime.py)
registra hash do executavel e logs. Evidencias locais em target/p241-runtime-proof
e target/p241-runtime-release-proof. A fase de crash encerra somente o processo
filho criado pelo teste e verifica recuperacao de valor confirmado por PUBACK.
As paradas normais receberam Ctrl+Break e retornaram codigo zero, com log
`durable broker shutdown complete`.

Primeiras tentativas: cache profundo falhou no include C do AWS-LC; teste novo
falhou por import faltante; Temp herdado recusou escrita. Corrigidos com caminho
curto permitido, import explicito e diretorio temporario proprio. Nao foram
contados como PASS. O lock raiz conserva todos os pacotes/versoes anteriores e
adiciona somente atomicwrites 0.4.4, rustix 0.38.44, linux-raw-sys 0.4.15 e
windows-sys 0.59.0. Cargo metadata --offline --locked validou o grafo.

## SCM, instalacao e limites

O runner [verify_windows_broker_scm.ps1](../../scripts/verify_windows_broker_scm.ps1)
prepara um teste reproduzivel em VM Windows descartavel elevada: recusa servico
existente, usa LocalService e ACL protegida em raiz unica, testa duas sequencias
start/stop, verifica listener e remove apenas o servico cuja identidade foi
criada por ele. O arquivo foi validado estaticamente; nao foi executado no host.

Nao se deduz teste de boot, SCM, UAC, ACL efetiva do MSI, bandeja real ou queda de
energia a partir de MQTT console ou encerramento abrupto de processo. O perfil
MSI permanece mTLS loopback e exige provisionar certificados/users/ACL antes de
iniciar. Nao cria credenciais fracas nem inicia automaticamente durante install.

Referencia tecnica: [MoveFileExW / MOVEFILE_WRITE_THROUGH](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw),
[atomicwrites 0.4.4](https://docs.rs/atomicwrites/0.4.4/atomicwrites/).
O codigo da dependencia foi inspecionado localmente para confirmar os flags.

## Empacotamento final

Diretorio completo: `dist/windows/p241-broker-0.43.0-candidate`.
Os diretorios p241 parciais anteriores nao sao a entrega final.

| Artefato | SHA-256 |
| --- | --- |
| xmqr-broker-0.43.0-windows-x64-experimental.msi | 42571dba7e94636cf50509062080eebe7d0ca8abcf0b8731c38445ec8a760a07 |
| xmqr-manager-0.1.0-windows-x64-experimental.msi | 9aa11d066d7f9fd59d834e50d81f5632eff8a7cb03f0c9f3172d9a42920c867d |
| mqtt-broker.exe release incorporado no MSI e testado por MQTT | 6da6816aefaf0975b49bc63a081bfa09f1e3c3a0b7b76ab6e6ae02409748141a |

Build release offline e marcadores PASS. Empacotamento estatico/WiX: 13/13 PASS,
incluindo compilacao de fixtures dos quatro tipos de MSI. 426 entradas SHA-256
verificadas. Notices/licencas para 147 dependencias do broker e 79 do manager.
Tres crates omitiam o texto de licenca no arquivo fonte distribuido; o coletor
agora usa fallback restrito a identidade/versao/licenca, com textos inalterados
e proveniencia/hashes em LICENSE-SOURCE-NOTES.md. Nenhum texto foi inventado.
O primeiro build parou nessa falta de textos; o build completo posterior passou.

Inventario raiz atualizado somente com quatro pacotes adicionados; comando
`python -X utf8 scripts/license_inventory.py --check` PASS com Cargo offline.
A invocacao sem UTF-8 antes falhou pelo locale cp1252 do Python no Windows.

ZIP de entrega: `dist/windows/xmqr-broker-0.43.0-windows-x64-experimental.zip`.
Primeira tentativa encontrou timestamp anterior a 1980 nos notices; apos
revisao v1.2, a exportacao limita os timestamps do container ZIP ao intervalo
suportado e conserva os bytes dos arquivos (verificados contra SHA256SUMS).
Inclui ambos os MSIs, install-windows.ps1, manifest, checksums, README e notices.
Instalacao coordenada apos extrair: `./install-windows.ps1 -Components broker`.
Esse comando nao foi executado no host. So o MSI do broker nao instala a bandeja;
o script coordenado inclui o manager. O gerenciador aparece no login normal
ou e aberto pelo script quando este e executado sem elevacao permanente.

ZIP final: 4406241 bytes, SHA-256
`f1cd9eca7fcd24dddc52c77b3344648a3928de8c08351bc93dd9e22a50619f0f`.
A integridade ZIP e os 426 checksums dos arquivos extraidos logicamente foram
verificados. A sessao atual confirmou Administrator=False; consulta CIM da
maquina foi recusada. Nao ha VM descartavel elevada acessivel nesta sessao para
executar o gate SCM. Isso e uma limitacao de ambiente, nao um teste aprovado.
