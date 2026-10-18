# P201 — pacotes MQTT 5 exclusivos do servidor

- [Prompt P201](../broker/201-server-only-control-packets-mqtt5.md) criado e enviado antes do código em `73113c8`. Fonte implementada e publicada em `c5464871dd3888ff31571cafff73b1d15012a5df`.
- Após CONNACK, CONNACK, SUBACK, UNSUBACK e PINGRESP recebidos do client são classificados antes de interpretar o corpo como erro de protocolo do emissor. O broker envia DISCONNECT `0x82` com o escritor limitado pelo Maximum Packet Size e fecha. MQTT 3.1.1 conserva o fechamento anterior; outros tipos e flags não mudaram.
- Unitário cobre os quatro tipos com corpo vazio ou inválido, preserva PINGREQ válido e compara 3.1.1. Fixture TCP com broker real confirma `0x82`, fechamento, Will e operação normal em nova conexão. Regressões P194 (segundo CONNECT) e P200 (flags reservadas) PASS.
- Gates locais Ubuntu 26.04/WSL PASS: fmt, suíte Rust (217 testes de biblioteca aprovados/6 ignorados e demais alvos PASS), Clippy `-D warnings`, build release, inventário de licenças, seis contratos de distribuição e fixtures TCP. [CI da fonte exata](https://github.com/licodevone/xmqr/actions/runs/39106546031) PASS em `rust` e `ubuntu-package`, incluindo a nova fixture.
- Recorte 6A parcial; cabeçalhos reservados e matriz normativa completa seguem abertos. Estado v15 e versões publicadas não mudaram. Sem tag/release isolada; P202 prepara o marco 0.36.0.
