# P261 - execucao do candidato Oracle Installer 0.1.0-rc.1

Data: 2026-11-03. Prompt: ../broker/261-versioned-oracle-installer.md v1.2.

## Escopo e entrada

Pedido explicito: nova versao para futuras instalacoes, envio ao GitHub,
nova tag/release e copia do pacote na pasta local solicitada. Instalador
independente; broker/client0.43.0 e admin0.11.0 continuam fixados por SHA.
Base local7c7a989; publicacao baseada no main remoto5cf71dc237fb033cc7a72aceb2f1f882d72bcd23
para preservar o commit remoto posterior. Nenhum arquivo fonte Rust alterado.
Alteracoes locais preexistentes e dados operacionais excluidos da publicacao.

## Implementacao

Comparacao completa da bridge; ID pos-negativo reduzido de25 para16;
preflight de CLI real antes de PKI; retomadas com checkpoint restrito;
preservacao de PKI/credenciais/configuracao/estado na retomada MQTT.
ZIP deterministico por allowlist, manifesto e hashes; sem arquivos privados.
Harness de ciclo systemd exclusivamente em runner GitHub hospedado descartavel.

## Evidencia local real

- Parser clientWindows0.43.0: 5 IDs validos chegam ao erro de leitura de senha
  ficticia inexistente, sem rede; ID24 recusado. CLI_PREFLIGHT_PASS cases=6
  versions=1. O binario Windows local tem diferencas adicionais vs tag;
  esta evidencia nao substitui os pacotes Ubuntu fixados.
- Compilacao Python: 3 scripts, 2 programas Python internos do harness e3
  blocos Python do instalador PASS.
- Empacotamento duas vezes em diretorios temporarios: bytes identicos PASS;
  manifesto/integridade do ZIP extraido PASS; adulteracao do README recusada.
- Bash/systemd/Docker locais BLOCKED por runtime/IPC indisponiveis ou negados.
  Sem contorno desses bloqueios e sem acesso SSH do agente a VPS.
- Gates Rust NOT_APPLICABLE: nenhum Rust/Cargo alterado por este instalador.

## Gates de publicacao, inicialmente pendentes

A branch installer/oracle-0.1.0-rc.1 executara fresh, bridge-resume e
mqtt-resume no mesmo commit. A CI inclui os pacotes oficiais reais, mTLS,
QoS1, retained/restart, senha invalida recusada, observador401/200 e3
servicos ativos. Fixture legado reproduz as duas falhas antes da retomada;
MQTT compara materiais privados internamente sem exportar hashes/arquivos.
Checkpoint completo deve recusar retomada sem mudar status ou servicos.

Nenhuma execucao remota PASS e reivindicada neste registro de entrada.
O workflow publica a tag imutavel oracle-installer-v0.1.0-rc.1 e prerelease
somente depois dos tres gates e da verificacao deterministica. EVIDENCE.json
no ZIP referencia SHA/run/resultados efetivos. Assets remotos devem ter o
mesmo tamanho/SHA dos arquivos gerados. Sem mudanca de latest.

## Limites

Container Ubuntu26/systemd nao comprova kernel/rede OCI nem recuperacao da
VPS do operador. Esta exige XMQR_INSTALL_PASS separado. Candidato experimental,
sem conformidade MQTT integral ou aceite de producao. Sem ARM/upgrade generico,
abertura de firewall, mudanca de cobranca ou alteracao de tags existentes.

## Resultado efetivo da tentativa de publicacao e entrega local

GitHub create-tree:403 Resource not accessible by integration, tanto com
workflow quanto sem .github. Leitura do repositorio funciona e a conta possui
push, mas a integracao recusou a escrita. Nenhum commit/branch/tag/release
foi criado. Plugin GitHub confirmado instalado; nao alterar permissoes sem
pedido e nao contornar bloqueios de rede/IPC. Gates Ubuntu BLOCKED.

P261 revisado para v1.2 antes do ajuste de manifesto. validation.status agora
explicita NOT_RUN no pacote local sem evidencia Linux. Gates PASS continuam
obrigatorios na publicacao. Repeticao local apos ajuste: Python PASS,
ZIP deterministico2x PASS, integridade PASS, adulteracao recusada PASS,
guarda contra privilegios no host local PASS (nenhum Docker executado).

ZIP candidato e checksum entregues na pasta raiz local pedida pelo usuario.
Integridade do ZIP entregue revalidada por extracao temporaria e verificador;
nao representa release publicada nem recuperacao da VPS.

## Retorno do operador - retomada MQTT na VPS, 2026-11-03

Operador executou --resume-mqtt apos checkpoint FAILED stage=mqtt-smoke exit=2
e enviou o resumo final Broker TLS/Painel por tunel/validade/ACL. No script
0.1.0-rc.1 esse trecho e emitido apenas depois de enable-services, verificacao
de3 units ativas, readiness e escrita do status PASS. O recorte enviado nao
inclui literalmente XMQR_INSTALL_PASS nem o transcript integral dos testes.
Evidencia de conclusao pelo fluxo do instalador; proximos passos orientados:
consultar status das units e abrir o painel pelo tunel SSH local19080.
Nenhuma nova execucao do instalador e necessaria. Conectividade MQTT externa
nao foi demonstrada; firewall/OCI continuam sem alteracao pelo instalador.
A matriz CI Ubuntu (fresh e duas retomadas), tag e release continuam pendentes
por bloqueio403 da integracao GitHub; este retorno nao inventa esses gates.
