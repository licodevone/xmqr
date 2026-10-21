# P242 - Client e admin nativos Windows

Prompt: [P242 v1.3](../broker/242-windows-client-admin-runtime.md).
Pedido: continuar o client e o admin após o broker, com agentes em paralelo.
Execução: 2026-10-21, Windows x64 MSVC, toolchain instalada Rust 1.99.1.
MSRV declarado não ensaiado nesta execução. Sem commit/push/tag ou mudança de versão.

## Escopo e autoria

- C151, agente de implementação: `xmqr-client`; normal e adaptador separados.
  [Registro C151](../../../xmqr-client/prompts/registros/C151-windows-private-runtime.md).
- A27, agente de implementação: `xmqr-admin`; pin Git do core preservado.
  [Registro A27](../../../xmqr-admin/prompts/registros/A27-windows-private-runtime.md).
- Empacotamento, agente independente: MSIs, notices, provisionamento e runner SCM.
- Integração, agente principal: fixture TLS/hash, runner mTLS/HTTP, evidências e entrega.

Estado anterior P239/P241/C150/A26 preservado, assim como alterações locais do
operador em AGENTS.md, docs/chat e `.serena/project.yml`. Cada árvore contém
mudanças ainda não commitadas; o commit no manifesto é base, não representa o
conteúdo completo dos executáveis. Os hashes identificam os artefatos testados.

## Resultado implementado

Client e admin validam owner/DACL por handles nativos; recusam permissões amplas,
DACL nula/vazia, ACEs desconhecidas, reparse points e aliases UNC/device/ADS.
Contas permitidas: identidade atual, SYSTEM, Administrators e LocalService.
Não inferem privacidade por atributo read-only nem desativam a proteção no Windows.

O client oferece `--service-config ABS_CONFIG` para executar a mesma preparação
sem SCM. Configuração versão 1 contém argumentos não interativos e arquivos
absolutos; subscriber exige saída JSONL privada existente. O limite padrão é
8 MiB; erro de capacidade interrompe o consumo, preserva os registros existentes
e impede ACK antecipado. Escrita, flush e sync_data antecedem PUBACK/PUBREC.
Não há rotação automática nem promessa exactly-once: crash entre sync e ACK pode
duplicar saída. Bridge/outbox e journal inbound QoS2 durável continuam Linux.

O admin cria/lê token privado, permite usuários estáticos e autenticação do painel
loopback por token ou login. `users_file` opcional mantém compatibilidade da
configuração versão 1. O template usa `state/token` e `state/users.json` para
separar configuração somente leitura do estado gravável por LocalService.
Bootstrap/login persistem após reinício. Bundle dinâmico/canal Unix/backup
mantêm seus limites existentes; o core fixado não foi substituído.

Os adaptadores receberam correções de STOP durante inicialização/status e
encerramento console Ctrl+Break. Controle real pelo SCM ainda não executado.

## Testes executados

| Gate | Resultado |
| --- | --- |
| Client, suite adaptador Windows | 95 PASS, zero ignorados |
| Client, CLI normal Windows | 93 PASS, zero ignorados |
| Client, builds normal `--bins` e adaptador | PASS |
| Client, Clippy estrito CLI normal e todos os targets do adaptador | PASS |
| Admin, suite adaptador Windows | 31 PASS, zero ignorados |
| Admin, CLI normal Windows | 29 unitários + 2 integrações PASS |
| Admin, builds normal e adaptador; ambos Clippy estritos all-targets | PASS |
| Client/admin, fmt e diff checks | PASS |
| Integração inicial debug | 9/9 PASS |
| Integração final release | 12/12 PASS |

O client normal preserva aviso preexistente unused_mut no bridge; o gate estrito
normal foi do binário mqtt-client. O broker mantém seus avisos Windows anteriores.
Não declarar Clippy global dos três projetos aprovado. Inventários de licenças
normais foram atualizados e conferidos sem alterar versões existentes do lock.

Integração release reproduzível na raiz do broker, escolhendo saída nova:

```powershell
python scripts/verify_windows_client_admin_runtime.py `
  --broker target/windows-msi/x86_64-pc-windows-msvc/release/mqtt-broker.exe `
  --client ../xmqr-client/target/windows-msi/x86_64-pc-windows-msvc/release/mqtt-client.exe `
  --admin ../xmqr-admin/target/windows-msi/x86_64-pc-windows-msvc/release/xmqr-admin.exe `
  --hash-fixture tools/windows-validation-fixture/target/debug/xmqr-windows-validation-fixture.exe `
  --output target/p242-runtime-packaged-release-proof
```

Saída real: código 0, report.json PASS. Cenários:

1. MQTT 3.1.1 e 5, ambos QoS1 e QoS2: publicação retained mTLS e assinatura via
   configuração de serviço, com conteúdo conferido no destino NDJSON privado.
2. Publisher pela configuração de serviço e subscriber contínuo com Ctrl+Break.
3. Destino cheio: erro sem truncamento; peer mTLS controlado confirmou PUBLISH
   recebido pelo client sem PUBACK no fio quando a escrita é recusada.
4. Senha incorreta, CA não confiável e SAN incorreto recusados.
5. Admin sem token/token incorreto HTTP401; token válido HTTP200 e broker ready.
6. Bootstrap/login por cookie, senha incorreta HTTP401 e login após reinício,
   usando a base privada de usuários persistida.

| Executável release testado | SHA-256 |
| --- | --- |
| mqtt-broker.exe | bdcf6eabafd70a8206916c4fd078bda002e2f0fb257bf3bc6b1c549f53882fff |
| mqtt-client.exe | 39c5f170849d2a514c31c13468625790cd362786a3a09846cc2d98169398d69d |
| xmqr-admin.exe | 1363dfb1277d1f9d5ac829e8ec46e18799ea13ea1d555788a3f2d1514201a482 |

Relatórios intermediários em `target/p242-runtime-debug-proof/report.json` e
`target/p242-runtime-release-proof/report.json` e
`target/p242-runtime-packaged-release-proof/report.json`; evidência durável sem segredos
em [results](../../docs/results/p242-windows-client-admin-runtime-20261021.json).

## Falhas encontradas e correções

- Cache Cargo compartilhado perdeu manifests/archives. Causa não comprovada.
  Restaurados caches separados client/admin/packaging a partir de archives
  conferidos com SHA256 dos locks; mtime atualizado, TMP/TEMP privados por build.
  Cache não foi apagado durante builds. Todos os gates finais passaram.
- OpenSSL do Git recusou objetos MSYS no sandbox; Python não tinha crypto/Argon2.
  Fixture TLS nativa .NET, sem tocar certificate store, e helper Rust Argon2
  somente de teste resolveram a execução. Helper usa salt fixo de teste,
  nunca é provisionador real nem integra os MSIs.
- Verificador TLS estrito expôs SKI/AKI ausentes na fixture; extensões adicionadas,
  preservando verificação normal. Não foi usado insecure/no-verify.
- API de segurança inicialmente usava UNKNOWN_OBJECT, erro87; clientes corrigidos
  para SE_FILE_OBJECT e reexecutados com arquivos reais protegidos.
- Teste preexistente do client assumia Linux fora de cfg; separado do negativo
  Unsupported em Windows. Teste de junction usa um reparse real verificado;
  criação de junction própria foi negada pelo ambiente, sem skip disfarçado.
- O primeiro empacotamento completo parou por falta de LICENSE na dependência
  windows-permissions0.2.4, declarada MIT. Incluído fallback restrito com texto
  canônico MIT de permissão/disclaimer, manifests originais como atribuição e
  hashes/proveniência; nenhuma autoria/ano inventados ou notice alheio usado.
  O coletor continua recusando outras omissões não revisadas.
- Rebuild final incorporou ajustes do admin após a primeira prova release,
  alterando seu hash. Reexecutados os 12 cenários contra os executáveis exatos
  do pacote; todos passaram. Não reaproveitar o hash anterior como prova final.

## Provisionamento e aceitação restante

Arquivo criado pelo operador pode continuar com seu SID como owner/ACE, mesmo
num console elevado. LocalService deve recusá-lo. Não basta executar token-init
como administrador: normalize owner para Administrators e DACL protegida somente
SYSTEM/Administrators/LocalService, incluindo o pai imediato privado.
`provision_windows_service_file.ps1` prepara um arquivo existente e seu pai,
com opção de escrita para saída/estado; exige elevação e metadados HKLM do
componente instalado, limita-se ao ProgramData dedicado e recusa reparse/traversal.
Não muda árvores arbitrárias nem revela conteúdo dos arquivos.

Os runners `verify_windows_broker_scm.ps1` e
`verify_windows_component_scm.ps1` dão um ensaio concreto para VM descartável
elevada, recusando serviços/MSIs já presentes e removendo apenas o próprio
serviço de teste. Não foram executados no host. Esta sessão não tem token
administrativo; consulta SCM/CIM foi negada. Isso não prova presença nem ausência
de serviços instalados. Nenhum serviço/MSI foi instalado por esta execução.

Permanecem NOT_RUN: instalação MSI e ACL efetiva do instalador/LocalService,
ciclo SCM real, UAC, boot/login, bandeja com componentes instalados, upgrade,
rollback/reparo/remoção. Os testes acima são processos console reais em Windows,
não aceitação dessas etapas. Manifesto deve manter native_acceptance=false.

## Pacote

Build/notices/WiX, hashes de MSI e ZIP são registrados na evidência durável
citada acima após conclusão do empacotamento. Pacote experimental, sem assinatura;
configurações exigem credenciais/certificados provisionados antes de iniciar.

Candidato final: `dist/windows/candidate-p242-full-20261021-145834`.
`python scripts/verify_windows_packaging.py --wix`: 13/13 PASS. Notices de 79
dependências do manager, 147 do broker, 147 do client e 197 do admin, com
1.033 checksums conferidos. Corrigidos exemplos de caminho do helper para
backslashes e `client-default`. Nenhum MSI foi instalado.

| MSI | SHA-256 |
| --- | --- |
| xmqr-manager-0.1.0-windows-x64-experimental.msi | 06e66938de1545ce6fa00004278ed7fc02c1de9551a38ca127380ec272fca242 |
| xmqr-broker-0.43.0-windows-x64-experimental.msi | 57ffea517d842398bf3555de71e6f86d2279c2adb953cbe0e41bdf86455faed3 |
| xmqr-client-0.43.0-windows-x64-experimental.msi | de9474882f2679d078ad007996d985bcae18fb538aa75e75f1bc32cff3bb6ce8 |
| xmqr-admin-0.11.0-windows-x64-experimental.msi | d9535f757167ae5f62ef103c7f2f1b173f3c464a691b5b81b3ddd194dafaed17 |

ZIP: `dist/windows/xmqr-windows-broker-client-admin-20261021-experimental.zip`,
9.426.726 bytes, SHA-256
`f6a96e965da096821668fd1c23f5d4d9a644d50e581efbebe0ad7199bcab77d1`.
CRC do ZIP e todos os 1.033 hashes internos conferidos. Contém quatro MSIs,
README, manifesto, notices, instalador coordenado e helper de provisionamento;
exclui os arquivos de debug WiX. Sem certificados/chaves/senhas/estado de teste.
Após extração, o comando de instalação seletiva documentado é
`./install-windows.ps1 -Components broker,client,admin`; ele inclui a bandeja,
mas exige provisionamento e validação em VM antes do uso operacional.
