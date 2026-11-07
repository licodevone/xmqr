# P261 v1.2 — instalador Oracle versionado e recuperação de mqtt-smoke

Data: 2026-11-02, America/Sao_Paulo. Pedido do usuário: criar uma nova versão
para futuras instalações após falhas repetidas no instalador.

## Entrada

Broker HEAD7c7a989/runtime0.43.0, client0.43.0/bridge0.5.0 e admin0.11.0.
P260 criou instalador ainda sem versão própria; erro de comparação da saída
bridge foi corrigido emv1.7. Operador agora reporta FAIL em mqtt-smoke com
fim da ajuda CLI. ID pós-negativo25 excede limite23 de MQTT3.1.1 na tag043.
Prova local adicional: clientWindows043 rejeitou25 com mensagem de limite;
ID16 foi aceito pelo parser e falhou depois na senha fictícia inexistente,
antes de rede. CLIWindows local tem42 linhas adicionais vs tag; não confundir
essa prova de parser com integração Ubuntu/pacote exato.

Todos os arquivos preexistentes, inclusive fontes admin A29 e logs, permanecem.
Sem acesso SSH do agente. Docker CLI existe, mas API npipe foi negada no
ambiente; Bash Git também bloqueado porIPC. Não contornar esses bloqueios.

## Objetivo e escopo

Entregar candidato **XMQR Oracle Installer 0.1.0-rc.1**, separado das versões
dos três programas. Não alterar Cargo, protocolo, estado ou binários core
para corrigir erros de automação. Aceite/publicação não antecipados.

Arquivos: scripts/install_oracle_x86.sh; scripts/verify_oracle_installer.py;
scripts/package_oracle_installer.py; docs/oracle-install-manual.md;
docs/oracle-instance.md; docs/releases/oracle-installer-0.1.0-rc.1.md;
prompts/registros/P261-versioned-oracle-installer.md; histórico diário.
Artefatos gerados em dist/oracle-installer/0.1.0-rc.1, sem credenciais.

## Requisitos

- --version do instalador, ZIP de arquivos allowlist, manifesto com SHA256
  de cada arquivo e pacotes oficiais, SHA256SUMS e checksum do ZIP.
- Corrigir ID25; manter mTLS/SAN, ACL, token privado, painel loopback19080.
- --resume-mqtt restrito a checkpoint privado mqtt-smoke, binários exatos
  e caches íntegros; preservar estado, PKI, senha, token, bundle e units.
  Não repetir APT/download/useradd/configuração nesse modo.
- Verificador stdlib: integridade do pacote, strings de versão dos executáveis
  reais e argumentos CLI de cada ID do script, usando senha fictícia
  inexistente para parar antes de qualquer conexão. Controle negativo com
  ID24 deve ser recusado pelo parser. Não ler dados/credenciais reais.
- Testes completos MQTT/admin permanecem no instalador e serão repetidos
  na VPS pelo operador. Erros com etapa/primeira linha e stderr privado por
  tentativa, sem dados sensíveis. Falha para os serviços retomados e preserva
  arquivos. Não tornar a retomada um bypass genérico.
- Novo host: validar sintaxe e preflight de CLI depois dos pacotes e antes
  de gerar credenciais. Novas correções exigem nova versão candidata.

## Aceite/validação

1. Integridade/manifesto/ZIP determinístico verificável e sem arquivos privados.
2. Regressão de parser Windows real: casos válidos chegam somente ao erro
   de senha fictícia; controle ID24 retorna limite23. Documentar plataforma.
3. Bash/Python e smoke Ubuntu26 requerem execução real; falta de runtime é
   BLOCKED, não PASS. Versionar candidato não publica release aceita.
4. Probes MQTT QoS1, retained/restart, autenticação negativa e painel devem
   terminar XMQR_INSTALL_PASS na VPS, comprovado por retorno do operador.
5. Sem commit/push/tag/release ou ampliação de firewall nesta etapa; autorização
   de novo candidato não equivale à publicação de binários não homologados.

## Revisao v1.1 - publicacao autorizada, 2026-11-03

O usuario autorizou explicitamente commit/push, nova tag e release no GitHub,
e pediu copia do pacote na pasta raiz local do agrupamento. Esta autorizacao
substitui a restricao do item5 acima; os gates de aceite continuam obrigatorios.
A publicacao sera prerelease experimental independente, sem alterar Cargo,
latest ou tags anteriores. Branch installer/oracle-0.1.0-rc.1 baseada no main
remoto5cf71dc; tag prevista oracle-installer-v0.1.0-rc.1 no commit validado.

Escopo ampliado: packaging/oracle-installer/{README.md,Dockerfile.ci},
scripts/test_oracle_installer_ci.py e .github/workflows/oracle-installer.yml.
Os arquivos de CI iniciais foram preparados durante esta revisao de escopo;
nenhuma execucao Ubuntu ou publicacao foi antecipada como PASS. Conferir o
fixture de regressao e validar sintaxe Python interna antes do primeiro envio.

Gates novos: tres cenarios Ubuntu26/systemd em runner GitHub hospedado
DESCARTAVEL (fresh, bridge-resume, mqtt-resume), incluindo reproducao das
falhas legadas, preservacao dos materiais privados e recusa sem mutacao apos
checkpoint completo. O harness recusa execucao privilegiada no host local.
Depois: empacotamento deterministico duas vezes, integridade do ZIP extraido,
tag imutavel no SHA exato e prerelease com ZIP+checksum. Comparar digest e
size dos assets publicados com os arquivos gerados. Evidencia publica sem
PKI/senhas/tokens/estado. Nao incluir logs operacionais nem mudancas alheias.

A CI substitui a falta de runtime Linux local para os gates deste candidato;
a VPS do operador continua exigindo XMQR_INSTALL_PASS separado. Se qualquer
gate falhar, revisar este prompt antes de corrigir e repetir no novo commit.
Somente depois do aceite copiar os bytes identicos da release para a pasta
local solicitada. Nao declarar a VPS recuperada sem evidencia do operador.

## Revisao v1.2 - bloqueio GitHub e entrega local

A API create-tree retornou403 Resource not accessible by integration tanto
com o workflow quanto em tentativa reduzida sem .github. Leitura do repositorio
funciona; permissao push do usuario nao equivale a permissao de escrita da
integracao. Nenhuma branch/commit/tag/release foi criada. Nao repetir os
mesmos writes nem contornar por credenciais/runtime alternativos.

Entrega local autorizada nao deve esperar permissao externa: gerar ZIP
candidato working-tree na pasta explicitamente pedida, com manifesto que
expresse validation.status=NOT_RUN quando nao ha EVIDENCE.json. Evidencia
PASS continua obrigatoria para o fluxo de publicacao automatica. O pacote
local nao deve ser anunciado como release publicada ou instalador homologado.
Validar novamente determinismo, manifesto, checksum e rejeicao de adulteracao
apos acrescentar o estado de validacao. Revalidar recusa do harness no host
local sem criar containers. Registrar gates Ubuntu BLOCKED e informar a
necessidade de habilitar escrita da integracao GitHub para concluir o pedido.
