# P248 - Inicio comprovado e correcao de Client persistente

Prompt broker/248-installed-startup-and-client-idle.md v1.0, 21/10/2026.
Base0fbe2dec e alteracoes locais anteriores preservadas. Client independente
base44e13a4b, versao0.43.0. Sem commit/push/tag/versao/novo MSI.

## Evidencias de entrada

P247 report2026-10-22T02:04:52.9208814Z + captura exata do operador:
Broker/Client/Admin Running inicialmente; preparo/inicio administrativo aceitos.
HTTP reais /health200, /ready200, /api/auth/config200 setup_requiredtrue.
Broker metricas total1/sessions1/active0 e rejeicoes auth/ACL zero. Codigo
session.rs Client subscriber tem90s aplicacao e nao renova PINGRESP. Politica
CLI e intencional mas incorreta para servico persistente sem total/count.
Estado atual SCM nao comprovado (GetService semvisibilidade/CIMnegado pelo
token das ferramentas); nao inventar evento de servico ou causa de log.
Proof semsegredos: target/p248-startup-proof.json. Nenhum hostfile alterado.

## Escopo e andamento

C152 do Client corrige somente runtime Windows-service/config privada MQTT3.1.1,
mantendo politica CLI e timeouts de protocolo/total/reconexao/QoS2/Stop.
Updater operadoradmin P248 e pacote binario serao entregues somente apos
novo build/testes; sem copiar exe antigo e sem reinstalar/preparar credenciais.
Agentes paralelos separados: fonte/testes/buildClient e updaterPowerShell.
Agenteprincipal: provasHTTP, empacotamento/icone/hashes/docs/registro/chat.

## Gates

Preparo/inicio inicial tres: PASS operador. HTTPBroker/Admin: PASS agente.
Sustentacao Client alem90s, hotfix nativo, aplicacao SCM elevada: pendentes
da conclusao C152 e operador. Este arquivo sera atualizado com resultados.

## Validacoes de empacotamento e atualizador

P248 revisado ate v1.5; C152 v1.6. Updater parseado e 16 casos isolados
PASS com arquivos temporarios: copia CreateNew, substituicao/backup/rollback,
recusa de hashes alterados, backup vazio/existente. Nenhuma execucao do
updater contra instalacao real. verify_windows_packaging.py:16PASS/1SKIP;
fixture --wix nao repetido. Parser build-windows PASS.

Tentativas de icone apos compilar: LoadLibraryEx com flag0x22 falhou Win32
32; retentativa limitada5s nao resolveu. Diagnostico AS_DATAFILE0x2 passou
9imagens/10recursos e integridade5secoes, mas CreateProcess retornou acesso
negado e as copias posteriormente nao estavam presentes. Defender/Operational
nao legivel: causa da indisponibilidade NAO comprovada. Binario bruto intacto.
Nenhuma protecao/ACL desabilitada. Estes hashes de copias nao sao entrega.

Alternativa legitima: build.rs do manifesto Windows-service compila ICO
com WindowsSDK rc.exe e o vincula no link nativo, sem deps/RUSTFLAGS novos.
Builder Client agora verifica somente leitura e copia bytes; prova --version
posterior tambem acrescentada ao fluxo de marca. Outros componentes preservam
seu fluxo existente; nao foram recompilados/instalados nesta fatia.

Novo verificador readonly: positivo ClientP246 PASS9imagens/10recursos;
negativo iconeAdmin PASS(recusa); hash preservado. Aguarda artefato C152 nativo.

## Resultado nativo final

PASS: fmt; Clippy all-targets -Dwarnings3.26s; suite100/100 (0.40s,
compile10.19s); release locked/offline7.50s. C152 compilado WindowsMSVC.
Icone SDK vinculado nativamente: readonly9imagens/10recursos PASS,
unchanged=true. Original e copia publica executam --version0.43.0 e
--windows-service-capabilities schema1/client/service_entrypointtrue.
Exe5.912.064bytes SHA256:
e9228b317a9618ee7502b7aa007d822f48ad07b109e8ac85fceceb72e014bf51.
Evidencia target/p248-native-icon-proof.json; sem mutacao pos-link.

Aceite instalado: PENDING operador elevated updater e observacao100s.
Broker/Admin nao alterados. Nao alegar boot/logon/atalhos/tray/MSI completos.

Conferencia inicial de pacote: FAIL por .toml publico de licenca em notices/,
nenhum ZIP criado. Prompt revisado1.6 antes de permitir manifests de terceiros
somente em notices; filtros de chaves/runtime, allowlist e hashes preservados.


Entrega ZIP verificada:271arquivos,3.155.321bytes; todos os SHA256SUMS conferidos
sobre bytes do ZIP e CRC PASS; sem arquivos runtime privados na allowlist.
SHA256ZIP e28d415f11f40b557b7f37c55f80973c62abf7a2d46d678a55bcdfb52cd873bc.
Usuario informou liberacao dos sistemas no Kaspersky; nao comprova retrospectivamente
causa das copias indisponiveis. Executavel nativo/copia continuam executaveis.



## Aceite instalado informado em 2026-10-22

Imagem image(20261022-032130).png lida: updater exibiu20/40/60/80/100segundos,
Atualizacao concluida e caminho de backup anterior em ProgramFiles Client.
Observacao instalada100s: PASS operador (evidencia da captura, nao SCM direto
pelas ferramentas). Consulta readonly posterior do agente: Broker /health200,
/ready200; Admin /api/auth/config200; metricas connections_active1,total2.
Nao inferir identidade da conexao por contador. Boot/logon, atalhos/tray e
ciclo completo dos instaladores continuam pendentes. Usuario relatou problemas
para abrir/baixar links; pasta local de pacote verificada presente, com exe,
prompts e instrucoes, fornecida como alternativa sem download.

