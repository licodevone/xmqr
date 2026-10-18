# P227A — VBI canônico MQTT5, em validação integrada

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
resultados são JSON exclusivos e cleanup limitado. WireGREEN aguarda ELF0.42
integrado fornecido pelo coordenador, que também fará suíte/Clippy/release.

## Limites e revisão

Testeswire desta fatia são open-labTCP sintético, não provaTLS/mTLS nem aceite
global6A–6D. Sem migração v15, produção/SLA/powerloss/Windowsbroker/ESP32 novo.
Skills xmqr-rust-mqtt, xmqr-tests e xmqr-security-review orientaram tipos,
negativos, bytes independentes e isolamento; não declararam segurança integral.
Sem push/tag/serviço do operador. Registro será complementado após wireGREEN.
