# P262 v1.2 - XMQR Manager no terminal Linux

Data: 2026-11-03, America/Sao_Paulo.

## Entrada e pedido

Usuario pediu funcionalidade como o Manager Windows para terminal Linux,
incluindo a instancia Oracle ja instalada. Broker HEAD local7c7a989, runtime
broker/client0.43.0, admin publicado0.11.0; alteracoes P257/P259/P260/P261 e
adminA29 preservadas. Oracle relatou resumo final da retomada MQTT. Sem acesso
SSH do agente; Bash/WSL/Docker locais bloqueados. Nenhuma intervencao na VPS
e comprovada por testes locais. Diagnostico dos paineis: tag admin4483a356
vs executavel Windows A28 SHA42687cfe..., funcionalidades A23/A24/A25 posteriores
sem incremento do manifest0.11.0. Nao atualizar admin nesta fatia.

## Objetivo observavel e escopo

Entregar script Python3 stdlib `xmqr-manager` 0.1.0-rc.1 independente: menu
interativo e comandos status/start/stop/restart/logs/paths. Consulta systemd;
opera somente broker, instancia configurada de client (oracle por padrao)
e admin existentes. Arquivos novos: scripts/xmqr_manager_linux.py,
scripts/test_xmqr_manager_linux.py, docs/linux-terminal-manager.md,
prompts/registros/P262-linux-terminal-manager.md e historico diario.

## Requisitos

- Nomes de units allowlist; instancia ASCII alfanumerica/underscore/hifen
  limitada64 sem caminho/escape/opcoes. Sem shell, caminho de executaveis
  fixado em /usr/bin/systemctl e /usr/bin/journalctl, timeouts finitos.
- Apenas units existentes; erro de consulta nao equivale a nao instalado.
  Masked/erro de carga bloqueiam mutacoes. Client iniciado/reiniciado exige
  /etc/xmqr-client/INSTANCIA.conf. Nunca inventar instancias em `all`.
- Consulta nao requer root; mutacoes exigem sudo/root; nao elevar internamente,
  nao criar sudoers/polkit e nao permitir pergunta de senha por systemctl.
- --dry-run prepara os comandos para revisao sem executar mutacoes.
  Acoes all sao uma transacao systemctl para as units conhecidas presentes;
  systemd resolve dependencias. Saida de erro do comando e exitcode preservados.
- Estado activo nao equivale a readiness MQTT nem entrega ao dispositivo.
  Menu mostra texto e cores opcionais em TTY; somente tres tipos de software.
- Logs finitos no terminal,1..1000linhas, por escolha explicita. Caminhos
  conhecidos listados sem ler configs, tokens, chaves, senhas ou payloads.
- Nao modificar/habilitar units, auto-start, firewall/SSH/OCI, configuracao,
  PKI, estado MQTT ou versoes Cargo. Sem kill, purge, update ou instalacao remota.

## Migracao e aceite

Sem mudanca de protocolo/persistencia/ACL; ferramenta opcional e removivel.
Distribuir fonte e instrucoes de copia para Oracle e instalacao local explicita
em /usr/local/bin/xmqr-manager, recusando sobrescrita inadvertida. Help/version
portaveis para revisao; operacao requer Linux com systemd ativo.

Validar sintaxe, CLI help/version, negativos de instancia/unidade/root/masked,
inventario indisponivel, bulk abort, dry-run sem mutacao e propagacao de erro
com backend simulado. Nao anunciar teste unitario como E2E systemd.
Lifecycle Linux real NOT_RUN/BLOCKED ate ambiente proprio disponivel ou retorno
do operador; jamais testar start/stop/restart nos servicos reais do usuario.
Gates Rust nao aplicaveis pois nenhum Rust/Cargo muda. Registrar resultados e
revisar este prompt antes de corrigir falhas. Sem commit/push/tag/release novos.

## Revisao v1.1 - reuso do Manager Ubuntu existente

Inspecao encontrou tools/linux-manager/backend.py, Manager desktop Ubuntu0.1.0
publicado em P256. Reutilizar seu inventario/validacao de ExecStart/allowlist,
estados e ordem de controle. Nao duplicar esse backend nem alterar desktop.
Esta revisao substitui caminhos/instancia/batch descritos acima quando divergirem.

Arquivos de implementacao: tools/linux-manager/terminal.py,
tools/linux-manager/tests/test_terminal.py, tools/linux-manager/build_terminal_zip.py,
docs/linux-terminal-manager.md e breve referencia no README do Manager.
Backend original fica intacto. Menu mostra instancias reais pub/sub/bridge;
client sem unit aparece como CLI, sem inventar oracle. Labels broker/client/admin
sao atalhos apenas quando o alvo e inequivoco; ids completos continuam aceitos.

Subclasse de terminal troca pkexec dos logs por journalctl direto. Adapter de
execucao fixa root para mutacoes e adiciona --no-ask-password ao systemctl,
sem polkit grafico nem sudo interno. --dry-run usa control_plan do backend,
faz preflight completo e imprime etapas, sem fazer mutacoes; estado incerto
bloqueia o plano. All segue ordem/revalidacao/aborto parcial do backend; nao e
uma transacao atomica systemd. Chamadas limitadas e erros genericos sem exibir
ExecStart/env/configuracao. Logs por escolha explicita, fixados nas300entradas
ja usadas no Manager desktop, sem argumentos livres de journalctl.

ZIP candidato inclui terminal.py/backend.py/README.md e SHA256SUMS por allowlist;
checksum externo. Sem tag/release nem mudanca dos pacotes existentes. Provar
integridade/determinismo da embalagem, CLI/menus, autoridade root, recusa de
units externas/mascaradas/ExecStart divergente, bulk abort e estados finais em
backend simulado. Testes desktop apropriados rodam sem GUI onde suportados;
testes POSIX/GTK nao executaveis no Windows devem ser indicados como BLOCKED.

## Revisao v1.2 - fechamento da embalagem e erros do menu

Primeiros14testes do terminal PASS em Windows com backend simulado; help e
version PASS. Revisao identificou que o menu capturava ManagerError e encerrava
sem codigo de falha. Propagar esse erro ao handler principal e acrescentar
regressao para nao anunciar sucesso. Acrescentar negativo de unit masked.
Uma aplicacao de patch foi recusada por cabecalho README divergente; nenhum
arquivo daquele patch foi alterado. Corrigir o contexto antes de reaplicar.
Pacote inclui launcher proprio xmqr-manager-terminal usando Python isolado
(-I) em /usr/local/lib/xmqr-manager-terminal. Instrucoes recusam destinos
existentes e preservam o Manager grafico. Embalar somente terminal.py,
backend.py, README, launcher, LICENSE e SHA256SUMS; ZIP deterministico com
checksum externo, sem arquivos operacionais ou credenciais.
