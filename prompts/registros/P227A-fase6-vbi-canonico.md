# P227A — VBI canônico MQTT5 e inventário de propriedades

Data2026-10-18. Pedido coordenado no P227 para corrigir lacuna normativa6A,
sem executar bridge/admin como desvio. Ownership:codec.rs, script próprio,
subprompt e este registro; nenhum mod.rs/router/store/CI/Cargo/client editado.
Prompt criado antes dos testes/código e commitado localmente em35e7fcd,
sem push. Revisões v1.1/v1.2 preparadas antes das respectivas alterações.

## Requisito e método

OASIS MQTT5 §1.5.5, MQTT-1.5.5-1 exige o mínimo de bytes no Variable Byte
Integer. Implementação anterior aceitava representações redundantes no
Remaining Length, Property Length e Subscription Identifier. Correção em
FrameReader aplica regra após negociação5 e no CONNECT5 inicial identificado
por fronteiras seguras. Cursor interno é usado somente por campos MQTT5 e
agora rejeita dígitos superiores redundantes. Mapeamentos existentes mantêm
DISCONNECT0x81/CONNACK0x81 limitado, sem mudança em mod.rs ou formato v15.
Sem versão nova, dependências ou permissões do operador.

MQTT3.1.1 preserva framing histórico, inclusive testeP58 e CONNECT/PING com
Remaining Length não mínimo. Valores canônicos e fragmentação continuam
aceitos. EOF/I/O, ausência do restante do cabeçalho, quota e codificações de
outros tipos não são reclassificados por comparação de mensagens de erro.

## RED efetivamente executado

`TMPDIR=/var/tmp cargo test --locked -j1 --lib mqtt5_vbi_ -- --nocapture`
no fonte0.42.0 antes do fix:8novos testes,2controlesPASS/6FAIL, launcherWSL
exit1; compilação85s. Falhas em aceitação de VBI redundante em inteiros,
RemainingLength estabelecido/inicial, propriedades e SubscriptionIdentifier.
Os controles canônicos e MQTT3.1.1 passaram. Não é falha ambiental ou do
novo runtime corrigido; é RED planejado e preservado.

`verify_phase6_vbi.py --label baseline --state-root /var/tmp` no ELF existente:
versão real `mqtt-broker0.41.0`, SHA256
`674963f56ab2def9297847a94f5e2388003824eb6d67b75db27e4c7fbbd1709f`.
20casos:2PASS/18FAIL,17.204s, exit1, cleanupPASS. Cópia privada imutável,
estado nativoLinux/portaefêmera, envMQTT limpo, nenhum log/estado real.
Report `../.artifacts/p227a-vbi-baseline-1.json`, harnessSHA
`51a9355ab7471089440dc602d3d3a212893399b86c5dd2271fc21a1ad47c7681`.
Esse0.41 nunca é apresentado como validação de0.42.

## GREEN local e pendências

Depois de revisão v1.1/fix:mesmo cargo direcionado,8/8PASS, exit0,
compilação24.15s, testes0.02s. Nenhum build full/release iniciado por este
agente. Rustfmt somente codec.rs PASS; ASTPython e git diff --check PASS.
Root foi avisado antes de cada cargo e recebeu liberação do cache após terminar.

Revisão v1.2 reforça controleswire sem diminuir asserções:CONNECT3.1.1
histórico, observador para Will indevido de CONNECT5 recusado e cabeçalho
VBI inválido já completo antes de chegar corpo (total21vetores finais).
O script captura versão/SHA da cópia do ELF e do próprio harness; todos os
resultados são JSON exclusivos e cleanup limitado.

## Wire GREEN no ELF integrado

Coordenador forneceu cópia congelada em
`../.artifacts/p227-binaries/mqtt-broker-integrated-0.42.0` após integrar ambos
os fixes P227A/P227C (fonte de código10d5081, sobre10bab60). Sem rebuild por
esta frente. Comando efetivamente executado no WSL:

```sh
python3 scripts/verify_phase6_vbi.py \
  --broker ../.artifacts/p227-binaries/mqtt-broker-integrated-0.42.0 \
  --label candidate --state-root /var/tmp \
  --report ../.artifacts/p227a-vbi-candidate-1.json
```

21/21PASS, exit0, cleanupPASS, 3.509s observados, concluído
2026-10-18T13:56:11Z. Versão lida da cópia privada:`mqtt-broker0.42.0`.
ELF SHA256:`46d79faf91220cdd59e43602c8f3528a2654463a6f71408c542a9c8638b4f809`.
Harness SHA256:`ccc8ecae90ccd18ecc98d27dc8876ad42453a2f2663576f853b6ff38f07fb064`.
Controles3.1.1/canônicos, RL2/3/4bytes, fragmentado/antesdocorpo, PropertyLength
em9contextos estabelecidos, SubscriptionID, CONNECT/Will inicial sem Will e
MPS4/5 passaram. ReportRED anterior não foi reescrito; contagens diferentes
são explicadas pelo reforço prévio v1.2, não por remoção de asserção.

## Matriz documental 6A

Revisão v1.4 do prompt preparada antes de
`docs/conformance/mqtt5-property-matrix.md`: contexto/direção/ID/tipo,
multiplicidade/valores/tetos locais, referência OASIS, símbolo e20grupos
unitários/21grupos de scripts. Estado IMPLEMENTED_TEST_AVAILABLE para impedir
que disponibilidade de teste vire PASS global. Emissões opcionais ausentes
separadas das entradas aceitas. Revisão por confronto fonte/testes/seções
OASIS e diff/check; não foi executado reader testing por agente independente.
Skill doc-coauthoring orientou estrutura e distinções de leitura sem perguntas
redundantes, pois o contexto/contrato já foi fornecido pelo coordenador.

A matriz revelou divergência R01:alias válido não mapeado+TopicName vazio
usa0x94, enquanto §3.3.4 caso3a descreve0x82. Coordenador confirmou fonte e
reservou correção separada P227D; não se afirma conformidade desse vetor por
W13 atual. Tetos Will e todas as fronteiras UP16 também não são apresentados
como exaustivamente testados. Nenhuma checklist geral foi fechada pela matriz.

## Limites e revisão

Após correção separada P227D, repetido o mesmo harness P227A congelado no
novo ELF `mqtt-broker0.42.0` SHA256
`dca22b2624b7f36175d4e939c640b6f5730220bcc9510580eef9054a6af8ef57`:
21/21PASS, exit0, cleanupPASS,3.963s. Report exclusivo
`../.artifacts/p227a-vbi-p227d-candidate-1.json`; harnessSHA permanececcc8ecae
completo já registrado. Fontes runtime novas emd28f832; nenhum report anterior
reescrito. Matriz passou a indicar R01 corrigida e testes P227D disponíveis,
sem alterar o aceite global nem os limites de evidência.

Testeswire desta fatia são open-labTCP sintético, não provaTLS/mTLS nem aceite
global6A–6D. Sem migração v15, produção/SLA/powerloss/Windowsbroker/ESP32 novo.
Skills xmqr-rust-mqtt, xmqr-tests e xmqr-security-review orientaram tipos,
negativos, bytes independentes e isolamento; não declararam segurança integral.
Sem push/tag/serviço do operador. Suíte/Clippy/release e aceite integrado ficam
com o coordenador. Commit local de código/harness/registro:10d5081, autorizado;
matriz/atualização deste registro serão commitadas separadamente.

## P227 v1.8 — marcador final exclusivo do VBI

Após revisão independente do executor, coordenador autorizou esta fatia sob
P227v1.8 já preparado: adicionar somente `print('P227_VBI_PASS')` depois da
guarda global que exige statusPASS. Nenhum vetor/oráculo, timeout, tipo de erro,
cleanup ou fonte runtime mudou. Não rodado Cargo nem editados módulos Rust.
O diff funcional do harness é uma linha, fora do caminho FAIL.

Reexecutado no ELF D congelado `../.artifacts/p227-binaries/mqtt-broker-p227d-0.42.0`
com versão real0.42.0 e SHA256dca22b2624b7f36175d4e939c640b6f5730220bcc9510580eef9054a6af8ef57:

```sh
python3 scripts/verify_phase6_vbi.py \
  --broker ../.artifacts/p227-binaries/mqtt-broker-p227d-0.42.0 \
  --label candidate --state-root /var/tmp \
  --report ../.artifacts/p227a-vbi-marker-candidate-1.json
```

21/21PASS, exit0, cleanupPASS,9.227s observados; `P227_VBI_PASS` emitido
somente no final. Harness novo SHA256:
`c913d3b26638fb2ead23d56189f3ebc1551af5364c776be48118df5a2a1f6b91`.
ASTPython/diff--check PASS. Report exclusivo acima, anteriores intactos.

Os reports anteriores a este ajuste usavam helper/harnessSHA256
`ccc8ecae90ccd18ecc98d27dc8876ad42453a2f2663576f853b6ff38f07fb064`
(o baselineRED inicial de20vetores usava51a9355a, já discriminado). Importadores
P227C/P227D terão helperSHA diferente ao repetir, sem mudança semântica;
o coordenador repetirá os gates integrados. Este teste no ELF D/v15 não é
aceite do futuro broker E/v16 ou client C129. Commit local somente deste
registro e do script, sem push/tag/versão/serviço do operador.
