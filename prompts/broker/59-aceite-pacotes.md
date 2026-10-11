# P59 — aceite isolado do ciclo de pacotes, revisão 1

## rev2.5 — documentação instalada na imagem mínima Ubuntu

Lifecycle real encontrou pacote correto, mas dpkg da imagem descarta
/usr/share/doc/* por /etc/dpkg/dpkg.cfg.d/excludes. Incluir caminhos docs dos
dois pacotes apenas no container descartável antes deAPT. Não afrouxar cmp,
upgrade/rollback ou hashes. Repetir lifecycle e registrar falha anterior.

Estado de entrada em 2026-10-11: broker HEAD 57d23c0; client independente
6ee5aa8. P55 tem implementação local e aceite Unix pendente. Nenhuma distribuição
WSL aparece em wsl.exe --list --quiet; Docker/Podman ausentes no PATH.

## Objetivo e escopo

Fechar a lacuna do harness de distribuição da fase 1: instalação de versões
anteriores, upgrade para pacotes candidatos e rollback explícito para os pacotes
anteriores de broker/client. Alterar packaging/test_package.sh e documentar
comandos, pré-requisitos e resultados em docs/phase1-package-acceptance.md e
prompts/registros/P59-aceite-pacotes.md. Sem codec, quotas, versões, commits ou
release neste subescopo; o agente principal coordena o marco.

Apresentado antes da implementação ao usuário e agente principal. Pedido de
finalização da fase 1 autoriza preparar e executar o escopo isolado.

## Requisitos e migração

- Exigir container descartável Ubuntu 26.04 amd64, root e confirmação explícita
  XMQR_DISPOSABLE_PACKAGE_TEST=1; recusar execução no host.
- Receber quatro caminhos absolutos exatos: broker antigo/client antigo e
  broker novo/client novo. Validar nomes, arquitetura e upgrade estritamente
  crescente para cada pacote antes de modificar o sistema. Sem globs.
- Publicar hashes SHA-256 dos artefatos e conferir dpkg-query depois de cada
  etapa, inclusive downgrade com --allow-downgrades.
- Preservar conteúdo editado de conffile, estado fictício e credencial fictícia
  por hash em upgrade e rollback; conferir conta/modos do diretório privado.
- Validar units instaladas sem habilitar serviços automaticamente; testar
  remove/purge preservando dados de operador conforme política existente.
- Não tratar sentinela fictícia como recuperação MQTT ou validação de systemd
  ativo. P55/integrações Unix reais e package lifecycle são gates distintos.

## Aceite e validação

sh -n do harness; negativos de argumentos/pré-requisitos quando shell disponível;
execução real em container Ubuntu com quatro pacotes nativos identificados,
sem reutilizar instalação do operador. Registrar exit codes e versões/hashes.
Somente PACKAGE_LIFECYCLE_PASS após todas as etapas é PASS de pacote. Ausência
de Linux/pacotes é BLOCKED, sem tag ou conclusão da fase 1 por documentação.
Após qualquer falha funcional, revisar este prompt antes de corrigir o harness.

## Revisão 2 — runner WSL solicitado na coordenação

Usuário informa Ubuntu26 instalado/aberto sob sua conta licod; a sessão
CodexSandboxOffline continua sem enxergar a distro. Não operar a instalação
existente nem escolher host SSH. Adicionar scripts/verify_phase1.py para o
usuário executar nas duas árvores atuais: pré-requisitos Linux/Python/cargo/git,
logs de HEAD/status, gates Cargo offline/locked, inventário, P54/P55/Will, C27
e C38 quando o harness específico estiver disponível.

Builds em diretórios separados por execução sob target; TMPDIR deve ser /tmp
nativo para permissões e estado isolado dos harnesses. Registrar todos os
exit codes em summary.json, continuar checks independentes após falha e
retornar falha agregada. Ausência de pré-requisito reportar BLOCKED.
Não instalar ferramentas, não chamar sudo/APT/systemctl, não usar /usr/bin
mqtt instalado ou /var/lib/xmqr. Ciclo de pacotes permanece exclusivo do
container descartável no harness separado. UNIT_INTEGRATION_PASS não fecha
a fase sem PACKAGE_LIFECYCLE_PASS real. Validação local: ast.parse/--help e
recusa de plataforma Windows antes de iniciar builds/processos.

### Revisão 2.1 — C38 e encerramento de filhos do runner

Harness C38 identificado: ../xmqr-client/scripts/verify_phase1.py recebe
--broker/--client/--report. Executá-lo com binários recém-construídos e JSON
no diretório desta execução. Ausência do harness é BLOCKED. Em timeout de
qualquer comando, terminar o grupo de processos filho do runner, sem operar
processos externos; evitar deixar broker de teste vivo após matar o harness.

### Revisão 2.2 — integridade das fontes validadas

Registrar snapshots antes/depois da execução: HEAD e SHA-256 dos arquivos
versionados e novos não ignorados em ambos os repositórios. Excluir artefatos
ignorados pelo Git (target/dist/runtime). Mudança de HEAD/arquivo durante os
gates invalida o aceite, mesmo quando comandos individuais passam. A saída
UNIT_INTEGRATION_PASS só representa gates de código; package lifecycle e
interop externa seguem NOT_RUN, phase1_accepted=false explicitamente.

### Revisão 2.3 — gate externo Mosquitto

Executar scripts/verify_interop.py --broker BIN construído nesta execução
quando mosquitto_pub, mosquitto_sub e stdbuf já estiverem disponíveis. Não
instalar ferramentas. Ausência gera BLOCKED específico; resumo external_interop
recebe status e log desse gate, em vez de NOT_RUN fixo. Trata-se de open-lab,
sem alegar TLS/mTLS/ACL externa ou conformidade completa. Lifecycle continua
separado/bloqueante para o aceite final da fase. Revalidar AST e recusa Windows.

### Revisão 2.4 — distribuir exemplo e guia TOML P52

Fase 1 publica P52 no marco aprovado. scripts/build_deb.py deve incluir
packaging/broker.toml.example e docs/architecture/configuration.md em
/usr/share/doc/xmqr-broker, somente para o broker. São material opt-in: não
ativar MQTT_CONFIG, substituir broker.env ou migrar configuração automaticamente.
Lifecycle exige presença/conteúdo dos dois arquivos no pacote candidato e
instalação, valida que rollback reflita exatamente os arquivos do pacote antigo
(incluindo remoção quando ausentes na base), sem perder conffile/estado/sentinela.
Revalidar AST do buildscript e sintaxe do harness; pacote real segue Unix BLOCKED.
