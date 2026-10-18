# P199 — CONNECT MQTT 5 estruturalmente inválido

Estado de entrada: broker/admin legado 0.35.0 publicado com P194–P197, estado durável v15; client independente 0.28.0 e admin independente 0.10.0. O leitor já tipa campos internos truncados (`MalformedPacketStructure`), mas o CONNECT inicial com estrutura inválida fecha sem CONNACK; a fase 6A continua aberta.

Objetivo observável: quando um CONNECT inicial identifica com segurança o protocolo MQTT 5, possui bloco de propriedades CONNECT íntegro e apresenta truncamento ou bytes extras em campos posteriores, recusar com CONNACK `0x81` se o Maximum Packet Size anunciado comportar os cinco bytes mínimos. Nenhuma sessão ou Will deve ser criada. MQTT 3.1.1 conserva o fechamento sem resposta MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §3.1 (CONNECT), §3.2.2.2 (motivos de CONNACK), §4.13.1 (tratamento de pacotes malformados). O limite de tamanho de saída deve vir exclusivamente de fronteiras de propriedade estruturalmente reconhecidas; não procurar bytes `0x27` em texto ou payload.

Escopo: `src/mqtt/codec.rs`, unitários, script TCP independente, CI, estado de conformidade M01/M02, registro e checklist. Classificar somente `MalformedPacketStructure` após cabeçalho e propriedades CONNECT íntegros; preservar erros semânticos, UTF-8, propriedades fora de contexto, flags, autenticação, ACL, quotas e P183–P197. Sem alteração de client/admin, versão ou estado v15 nesta fatia.

Aceite: casos com Client ID, Will, User Name/Password e bytes finais truncados/extra retornam `0x81` com limite >=5 e fecham sem sessão/Will; limite 4 não recebe CONNACK. Um `0x27` em campo binário/texto não vira Maximum Packet Size. CONNECT válido e MQTT 3.1.1 não mudam. Executar fmt, testes completos, Clippy, build release, inventário e distribuição, TCP real e CI da fonte exata; registrar falhas e manter P199 desmarcado até gates e CI PASS. A fase 6A global permanece aberta, sem tag/release isolada.
