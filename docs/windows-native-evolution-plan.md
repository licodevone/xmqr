# XMQR no Windows nativo — relatório de planejamento

**Estado histórico do relatório P193:** planejamento futuro, sem implementação ou homologação Windows nesta
entrega. A [fase 9](evolution-plan.md) continua desmarcada. Instalar os pacotes
Ubuntu no WSL e acessar o serviço pelo Windows não constitui uma versão nativa.
As versões publicadas permanecem no [guia de releases](current-releases-wsl.md).

## Atualização P239 - infraestrutura experimental

O [serviço e a bandeja](windows-service-tray.md) agora têm implementação
experimental separada dos builds convencionais. O texto de planejamento abaixo
preserva a avaliação P193; W2/W3/W4/W5/W6 continuam sem aceite global.
O [registro P239](../prompts/registros/P239-windows-services-tray.md) distingue
gates executados e bloqueios de persistência/ACL. Em 2026-10-21, dependências,
locks e builds dos três adaptadores foram comprovados, com 21 testes dirigidos
aprovados. Controle SCM real e W2/W3 continuam pendentes; os negativos reais
confirmaram as recusas de persistência/token nativos.

## Atualização P242 - client e admin

Em 2026-10-21, client C151 e admin A27 receberam proteção nativa de arquivos
privados por proprietário/DACL, com recusa de reparse points e aliases de
caminho. Pub/sub mTLS, saída privada limitada, parada cooperativa e painel
autenticado com usuários persistidos passaram em 12 cenários Windows usando
os executáveis release. Veja o
[registro P242](../prompts/registros/P242-windows-client-admin-runtime.md).
Esses resultados substituem os bloqueios de token/senha das avaliações
históricas; não encerram as fases globais abaixo. Instalação MSI, SCM real,
boot/login e bandeja com serviços instalados ainda exigem VM elevada.
Bridge/outbox do client e bundle/canal Unix/backup do admin conservam seus
limites de plataforma. Nenhum serviço foi instalado nesta execução.

## Situação dos três sistemas

Atualização P241 (2026-10-21): a persistência do broker descrita como bloqueada
na avaliação histórica abaixo foi implementada no Windows. Testes nativos de
IO/recuperação e MQTT após reinício/crash passaram. O
[registro P241](../prompts/registros/P241-windows-broker-runtime.md) mantém as
evidências e os limites: SCM, boot, ACL/instalação, bandeja real e queda de energia
continuam sem aceite global. Os marcos abaixo permanecem abertos.

| Sistema | O que existe | Lacuna para Windows nativo |
| --- | --- | --- |
| Broker `mqtt-broker` | CLI/adaptador SCM; P241 acrescenta persistência e testes MQTT nativos Windows. | Instalação/SCM/boot e ACL efetiva aguardam VM elevada; rotação Unix e backup legado têm escopo separado. Crash de processo não comprova recuperação após queda de energia. |
| Client `mqtt-client` | C151: pub/sub Windows mTLS, senha/configuração privadas e saída NDJSON limitada com sincronização antes dos ACKs; parada cooperativa validada. | SCM, MSI/upgrade, boot e interop externa ainda pendentes. Bridge/outbox e journal QoS2 permanecem Linux; crash pode duplicar a saída. |
| Admin independente `xmqr-admin` | A27: token e usuários privados nativos, painel HTTP loopback autenticado, bootstrap/login e persistência após reinício comprovados. | SCM/MSI/boot ainda pendentes. Bundle dinâmico usa o core fixado com política Linux; canal Unix e backup/restore não receberam equivalentes Windows. |

O `mqtt-admin` incluído no pacote do broker é legado e também requer avaliação
própria. Não substituir o admin independente por ele sem compatibilidade
de comandos, segurança e estado documentada.

## Ordem proposta e critérios de aceite

Cada linha exige prompt antes do código, registro, testes negativos e revisão do
checklist. Os executáveis portáveis são uma etapa intermediária; serviço e MSI
são marcos separados. Nenhuma linha está aceita por este documento.

- [ ] **W0 — contrato e ambiente:** escolher versões/arquiteturas Windows
  suportadas, MSRV/toolchain, política de conta de serviço, diretórios de dados
  e certificados, canais locais e assinatura de artefatos. Criar CI Windows
  com build e testes; verificar dependências e licenças. Medir comportamento em
  NTFS local, sem generalizar de `/mnt/c` ou de contêiner Linux.
- [ ] **W1 — client `.exe` portável:** publicar e assinar com TLS/mTLS, QoS,
  retained, sessões e reconexão; testar Ctrl+C, timeout, stdin, codificação,
  saída estruturada e segredo em arquivo com ACL. Usuários publisher e
  subscriber devem poder usar perfis/credenciais separados. Testar contra
  broker XMQR e Mosquitto com negativos de certificado, senha e ACL. Aceitar
  apenas o `.exe` portável quando esses fluxos passarem em Windows real.
- [ ] **W2 — broker `.exe` portável:** adaptar locks, gravação e sincronização
  do WAL/snapshot, troca atômica e recuperação para a semântica do Windows.
  Provar commit antes de ACK, exclusão de segundo writer, crash nos limites
  do commit, restart, retained, Will, sessões e downgrade/backup do documento
  v15. Proteger estado, chaves e bundle por ACL de NTFS; teste negativo com
  usuário sem permissão deve falhar fechado. Validar TCP/TLS/mTLS e limites
  de recursos no Windows real antes de chamar o broker portátil de aceito.
- [ ] **W3 — admin `.exe` portável:** definir canal local autenticado com
  isolamento equivalente ao socket Unix; adaptar token, usuários, bundle,
  auditoria e backup/verify/restore sem segundo writer. Exigir permissões
  privadas, não seguir links/reparse points indevidos e garantir escrita
  atômica/rollback. Testar operações online e offline, falha de escrita,
  concorrência e recusa de acesso com a conta do serviço.
- [ ] **W4 — serviço Windows:** registrar broker e, onde necessário, instâncias
  de assinatura/publicação do client. Validar inicialização, parada
  coordenada, reinício, recuperação após falha, identidade restrita,
  diretórios/ACL, diagnóstico e rotação de certificado/configuração. Serviço
  ativo por si só não comprova prontidão MQTT; exigir probe funcional.
- [ ] **W5 — MSI e ciclo de vida:** empacotar somente executáveis já aceitos.
  Testar instalação limpa, upgrade, rollback, reparo e remoção em VM
  descartável, preservando ou removendo configuração/estado conforme opção
  explícita. Verificar serviço, ACL, certificado, logs, PATH, assinatura,
  hashes e ausência de senha em argumentos ou arquivos públicos. Não instalar
  no computador do operador como parte do teste automatizado.
- [ ] **W6 — homologação conjunta:** matriz broker/client/admin na mesma
  versão de estado, MQTT 3.1.1 e subconjunto MQTT 5 anunciado, teste cruzado
  com Linux/WSL, TLS/mTLS, crash/restart, perda de rede, quotas e campanha de
  longa duração. Repetir em cada versão/arquitetura declarada. Publicar tag,
  `.exe`/MSI, checksums, notas de upgrade/rollback e limitações apenas após
  gates e CI da fonte exata.

## Decisões e riscos a resolver antes do código

1. **Durabilidade:** `sync_all` no arquivo não basta para afirmar que rename e
   criação de snapshot sobreviverão a falhas no Windows. Definir contrato de
   flush e testar recuperação realista em NTFS; separar crash de processo de
   perda de energia, que exige bancada apropriada.
2. **Privilégios e segredos:** escolher a conta do serviço e ACL dos arquivos
   privados. Negar inicialização se chave, token, bundle ou estado estiverem
   acessíveis além da política. Não transportar o modo `0600` Unix como se
   fosse uma ACL Windows.
3. **Canal administrativo:** selecionar mecanismo local e autenticação que
   preserve o isolamento atual; não expor ações administrativas por rede
   somente para contornar a ausência de socket Unix.
4. **Distribuição:** decidir se `.exe` portável e MSI terão releases separadas.
   Cada instalador deve declarar arquitetura, pré-requisitos, serviço,
   ownership de dados e política de desinstalação. A fase 9 só termina com
   instalação/upgrade/remoção e recuperação verificados, não com build verde.

Este relatório deriva dos repositórios locais inspecionados em 2026-10-18.
Não executou build, serviço ou instalador Windows; resultados Linux/WSL não
são evidência de homologação nativa.
