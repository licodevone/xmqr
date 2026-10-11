# P59 — aceite de pacote da fase 1

- Prompt: [P59 revisão 1](../broker/59-aceite-pacotes.md), apresentado antes de editar.
- Pedido: prosseguir e finalizar fase 1, com agentes paralelos autorizados.
- Data/plataforma: 2026-10-11, Windows, usuário da sessão CodexSandboxOffline.
- Entrada broker: 57d23c0d3008ad869f81b89abe243c3e9790ee85; client 6ee5aa8.
- Alteração paralela P58 preservada; nenhum arquivo codec/client/plano alterado.
- Skill aplicada: xmqr-tests, lida com AGENTS/CONTRIBUTING/matriz MQTT/P36.

## Alterações

packaging/test_package.sh substitui globs por quatro argumentos absolutos,
valida plataforma e metadados antes do APT, exige versões crescentes e container
explicitamente descartável. Confere versões instaladas e hashes de arquivos
de operador em upgrade e downgrade, units/contas/permissões, remove e purge.
Novo docs/phase1-package-acceptance.md documenta o comando isolado, evidência e
limites. Sem alteração de formato durável, dependências Rust ou versão.

## Execuções reais

| Comando/cenário | Resultado | Detalhe |
| --- | --- | --- |
| wsl.exe --list --quiet | BLOCKED / exit0 | Saída vazia, nenhuma distro disponível ao usuário da sessão |
| where.exe docker bash ssh podman | BLOCKED Linux | Apenas ssh.exe listado; Docker/Bash/Podman não estão no PATH |
| Caminhos padrão Docker Desktop/Podman | BLOCKED | Ambos ENOENT; não é inventário exaustivo da máquina |
| Git sh.exe -n packaging/test_package.sh | PASS / exit0 | Sintaxe POSIX validada via Git for Windows; não é runtime Linux |
| Harness sem argumentos | PASS negativo / exit2 | Usage, nenhuma instalação iniciada |
| Harness com quatro caminhos e sem opt-in | PASS negativo / exit2 | Exige XMQR_DISPOSABLE_PACKAGE_TEST=1; nenhuma instalação iniciada |
| Python 3.12.14 -X utf8 scripts/verify_state_limits.py --broker target/debug/mqtt-broker.exe --client ../xmqr-client/target/debug/mqtt-client.exe | BLOCKED / exit2 | Unix directory fsync is required; sete cenários NOT_RUN |
| Install/upgrade/downgrade/remove/purge em Ubuntu26 | BLOCKED / NOT_RUN | Sem Linux/container disponível e sem quatro pacotes candidatos nativos identificados |

O comando Python foi executado com caminhos absolutos equivalentes aos acima.
Nenhuma distro/ferramenta instalada, nenhum host SSH escolhido, nenhum serviço
do operador iniciado ou dado real acessado. A skill e instruções locais exigem
reportar pré-requisitos ausentes; ausência não vira PASS nem validação Windows
da persistência. Nenhuma alteração de fsync.

## Aceite e pendências

Sintaxe e recusas antecipadas aprovadas. Ciclo real de pacotes e gate de quotas
permanecem BLOCKED. O arquivo de estado do harness é sentinela fictícia:
compatibilidade MQTT exige testes Unix P55, Will e integração broker/client.
O script não comprova systemd ativo, TLS/mTLS ou interop Mosquitto.

Executar o harness em Ubuntu26 descartável com pacotes antigos/candidatos
nativos e registrar log/exit code/hashes/versões antes de aceitar fase 1.
Sem commit, push, tag, bump ou release feitos por este subagente.

## Revisão 2/2.1 — runner para WSL do usuário

O usuário informa Ubuntu26 aberto e softwares instalados sob sua conta licod.
A sessão automatizada continua com lista WSL vazia; a existência declarada do
Ubuntu não concede acesso à conta/sistema instalado. Nenhum serviço existente
foi operado. Criado scripts/verify_phase1.py com builds separados por execução,
TMPDIR=/tmp, Cargo offline/locked, logs de gates e summary.json, SHA-256 dos
binários e integração P54/P55/Will/C27/C38. Timeout termina o grupo de processos
filho do runner. O runner não instala software, acessa /var/lib/xmqr ou usa o
mqtt-broker/mqtt-client instalado; não inclui lifecycle de pacotes no host.

Python ast.parse: PASS/exit0 após integrar C38. --help: PASS/exit0. Execução
Windows com --client-root: BLOCKED/exit2 antes de criar diretório de build ou
processos. Git diff --check: PASS/exit0. Links locais P59/doc/registro verificados.
Runner real Linux: NOT_RUN/BLOCKED pelo contexto da sessão. O agente principal
fornecerá o comando à conta que tem acesso ao Ubuntu26 e analisará logs reais.
Nenhum PASS Linux, pacote, recuperação ou conclusão de fase inferido.

Revisão 2.2 registra HEAD/hash das fontes antes/depois dos gates em ambos os
repos, excluindo artefatos ignorados. Qualquer mudança durante validação é FAIL
e invalida aceite. Resumo mantém phase1_accepted=false, PACKAGE_LIFECYCLE e
interop externa NOT_RUN e imprime PHASE1_BLOCKED separado dos gates de código.
AST final PASS/exit0; runner Linux continua NOT_RUN pela sessão Windows.

Revisão 2.3 adiciona gate Mosquitto open-lab existente quando mosquitto_pub,
mosquitto_sub e stdbuf já estão disponíveis. Pré-requisito ausente vira BLOCKED
específico no resumo external_interop; gate executado registra status/log real.
Sem instalação de tools e sem alegar TLS/mTLS/ACL externa. AST final PASS/exit0;
negativo Windows BLOCKED/exit2 antes de builds/processos. Rust não repetido por
alteração apenas de orquestração. Lifecycle continua NOT_RUN separado.

## Revisão 2.4 — pacote P52 opt-in

scripts/build_deb.py inclui broker.toml.example e configuration.md em
/usr/share/doc/xmqr-broker para o broker. Não ativa MQTT_CONFIG, não substitui
broker.env e não altera pacote client. Lifecycle extrai old/new em temporário
do container, exige arquivos não vazios no candidato antes do APT e compara
conteúdo instalado após upgrade/rollback. Em rollback, arquivos ausentes na
base devem desaparecer; conffile/estado de operador seguem verificados por hash.
Python ast.parse build_deb.py PASS/exit0; sh -n lifecycle PASS/exit0. Build real
.deb e lifecycle Ubuntu continuam NOT_RUN/BLOCKED pelo ambiente, sem novo PASS
de instalação ou release. Root coordena demais alterações e commit.
