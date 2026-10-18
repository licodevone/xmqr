# MQTT 5 — matriz de propriedades do broker XMQR

Inventário técnico preparado pelo P227A em 2026-10-18, fonte integrada
`d28f832` (0.42.0), incluindo diagnóstico P227D. Não é certificação MQTT nem
aceite global das fases 6A–6D.
Esta matriz complementa, mas não substitui, o plano e os registros de execução.

## Como interpretar

- `C→S`: recebido pelo broker. `S→C`: emitido pelo broker. Will é um bloco do
  CONNECT; suas propriedades não são propriedades do CONNECT externo.
- `1`: no máximo uma ocorrência; `N`: repetível. Ausência de uma propriedade
  opcional não equivale a recusa do pacote inteiro.
- Tipos: `B` = byte, `U16`/`U32` = inteiro big-endian, `VBI` = Variable Byte
  Integer, `UTF8` = string prefixada por U16, `BIN` = bytes prefixados por U16,
  `PAIR` = duas strings UTF8. Comprimentos locais contam **bytes**, não caracteres.
- Todas as linhas de entrada e de emissão implementada têm estado de evidência
  **`IMPLEMENTED_TEST_AVAILABLE`**: código localizado e testes indicados. Isso
  **não** afirma que cada teste já foi executado no ELF integrado desta revisão.
  `OPTIONAL_NOT_EMITTED` identifica uma escolha de emissão, não entrada aceita.
- Um teste de aceitação/duplicidade não prova automaticamente todos os valores
  extremos. As lacunas explícitas da seção final impedem essa leitura.

Fonte normativa: [OASIS MQTT 5.0, edição OS de 07/03/2019](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
As referências abaixo são seções/requisitos para conferência, não reprodução
da especificação. Regra comum: §2.2.2 define contexto/tipo; §1.5.4 UTF-8;
§1.5.5 (`MQTT-1.5.5-1`) exige VBI mínimo. §4.13 distingue fechamento obrigatório
de resposta diagnóstica, considerando o tamanho máximo negociado.

## Limites comuns e símbolos

No [codec](../../src/mqtt/codec.rs), `FrameReader::try_take_packet`,
`frame_header`, `Cursor::{variable_integer,text,binary,bytes,end}` e
`decode_for_inner` delimitam os quadros antes do roteador. O pacote completo e
buffer são limitados a 65.536 bytes; payload de PUBLISH/Will a 4.096 bytes;
SUBSCRIBE/UNSUBSCRIBE a 256 filtros por pacote. Prefixos incompletos aguardam
dados; truncamento interno completo não é interpretado como outro protocolo.
`MAX_PARTIAL_FRAME_TIME` é 30 s, distinto do timeout inicial CONNECT de 3 s.

`TopicName`/`TopicFilter`, em [topic.rs](../../src/mqtt/topic.rs), aplicam o teto
local de 1.024 bytes sem normalização. `Cursor::text` rejeita UTF-8 inválido,
NUL, controles e noncharacters; a rejeição dos últimos dois grupos é política
mais restritiva admitida pelo protocolo. Dados BIN não recebem essa validação.

Conjunto local `UP16`, usado **somente** onde indicado: até 16 User Properties,
até 256 bytes por chave/valor e soma `5 + chave.len + valor.len` até 2.048 bytes
(ID e os dois prefixos U16 incluídos). CONNECT, ACK, AUTH e DISCONNECT **não**
usam UP16; continuam limitados pelas strings U16 e pelo pacote completo.

## Entradas CONNECT C→S

Símbolo comum: `mqtt5_connect_properties_supported`; a sondagem estrutural
`mqtt5_connect_maximum_packet_size` não autentica nem aplica sessão. Campo
desconhecido/contexto indevido é recusado; duplicidade/valores semânticos
indicados abaixo têm CONNACK 0x82 quando a resposta limitada é possível.

| Propriedade | ID/tipo | Multiplicidade, valores e tratamento no XMQR | OASIS | Testes |
|---|---|---|---|---|
| Session Expiry Interval | 0x11/U32 | 1; 0..U32_MAX segundos; padrão 0; passado à política de sessão, independente de Clean Start | §3.1.2.11.2 | T01, W01 |
| Receive Maximum | 0x21/U16 | 1; 1..65.535; zero recusado; padrão 65.535; limita PUBLISH QoS1/2 S→C | §3.1.2.11.3 | T01, W02 |
| Maximum Packet Size | 0x27/U32 | 1; 1..U32_MAX; zero recusado; limita todo pacote S→C. Abaixo de 5 não cabe CONNACK; abaixo de 7 não cabe o CONNACK de sucesso atual | §3.1.2.11.4 | T02, W03, W17 |
| Topic Alias Maximum | 0x22/U16 | 1; 0..65.535, padrão 0; saída usa no máximo 16 aliases por conexão | §3.1.2.11.5 | T01, T03, W04 |
| Request Response Information | 0x19/B | 1; 0/1; validado e descartado; Response Information não emitida | §3.1.2.11.6 | T01, W05 |
| Request Problem Information | 0x17/B | 1; 0/1; validado e descartado; não há emissão de Reason String/User Property diagnósticos | §3.1.2.11.7 | T01, W05 |
| User Property | 0x26/PAIR | N; nomes repetidos aceitos; validado e descartado, sem UP16 | §3.1.2.11.8 | T01, T14, W05 |
| Authentication Method | 0x15/UTF8 | 1; método suportado `PLAIN`; outro método → 0x8C; PLAIN sem Data → 0x86; transporte não TLS é recusado | §3.1.2.11.9, §4.12 | T04, W06 |
| Authentication Data | 0x16/BIN | 1; requer Method; envelope PLAIN deve conter autorização vazia, identidade e senha não vazias, UTF-8, sem campos extras; credenciais não são logadas | §3.1.2.11.10, §4.12 | T04, T18, W06 |

PLAIN é o mecanismo delimitado adotado, não suporte genérico a qualquer SASL,
challenge/response ou método AUTH. `serve_mqtt`/`plain_credentials`, em
[mod.rs](../../src/mqtt/mod.rs), fazem autenticação/associação ao principal;
PLAIN junto com User Name/Password do CONNECT é recusado com 0x82.

## Entradas Will, dentro do CONNECT C→S

Símbolo: ramo CONNECT de `decode_for_inner`; materialização em `StoredMessage`.
Singleton duplicado/PFI inválido resulta em recusa 0x82; propriedade de outro
contexto, estrutura ou UTF-8 inválida não cria sessão/Will aceito. Tetos locais
de texto/binário excedidos podem fechar sem CONNACK específico; ver limitações.

| Propriedade | ID/tipo | Multiplicidade, valores e tratamento no XMQR | OASIS | Testes |
|---|---|---|---|---|
| Will Delay Interval | 0x18/U32 | 1; 0..U32_MAX; padrão 0; armazenado separado do PUBLISH futuro | §3.1.3.2.2 | T05, W07 |
| Payload Format Indicator | 0x01/B | 1; 0/1; preservado no Will publicado; validação do conteúdo do payload não é feita pelo broker | §3.1.3.2.3 | T05, W08 |
| Message Expiry Interval | 0x02/U32 | 1; 0..U32_MAX; começa na publicação do Will, não no recebimento do CONNECT | §3.1.3.2.4 | T05, W09 |
| Content Type | 0x03/UTF8 | 1; até 256 bytes; preservado | §3.1.3.2.5 | T05, W08 |
| Response Topic | 0x08/UTF8 | 1; TopicName concreto, não vazio, sem +/#, até 1.024 bytes; preservado | §3.1.3.2.6 | T05, T17, W08 |
| Correlation Data | 0x09/BIN | 1; até 256 bytes; preservado sem exigir UTF-8 | §3.1.3.2.7 | T05, W08 |
| User Property | 0x26/PAIR | N; UP16; ordem e nomes repetidos preservados | §3.1.3.2.8 | T05, W08 |

## PUBLISH C→S e propriedades encaminhadas S→C

Símbolos: ramo PUBLISH de `decode_for_inner`, `FrameReader::try_take_packet`,
`encode_publish_with_subscription_ids`; `send_delivery` em mod.rs e
`remaining_message_expiry` no roteador. Metadados MQTT5 não são prefixados ao
payload de destinatário MQTT3.1.1. A normalização não modifica valores de texto.

| Propriedade | ID/tipo | Multiplicidade, valores e tratamento no XMQR | OASIS | Testes |
|---|---|---|---|---|
| Payload Format Indicator | 0x01/B | 1; 0/1; preservado. Broker não valida payload UTF-8; essa validação é opcional para o receptor | §3.3.2.3.2 | T06, W10 |
| Message Expiry Interval | 0x02/U32 | 1; 0..U32_MAX; ausência não expira; entrega calcula tempo restante; retenção/fila expiram sem renovar relógio | §3.3.2.3.3; MQTT-3.3.2-5/-6 | T07, W11 |
| Content Type | 0x03/UTF8 | 1; até 256 bytes; preservado | §3.3.2.3.9 | T06, W10 |
| Response Topic | 0x08/UTF8 | 1; TopicName concreto até 1.024 bytes; preservado; não cria uma resposta de aplicação automaticamente | §3.3.2.3.5 | T08, T17, W12 |
| Correlation Data | 0x09/BIN | 1; até 256 bytes; preservado byte a byte | §3.3.2.3.6 | T08, W12 |
| User Property | 0x26/PAIR | N; UP16; preserva ordem, valores e nomes repetidos no encaminhamento | §3.3.2.3.7; MQTT-3.3.2-17/-18 | T08, W12 |
| Topic Alias | 0x23/U16 | 1; C→S:1..máximo anunciado (0 ou 16); tabela local à conexão. Zero/excesso →0x94; válido ainda não mapeado + TopicName vazio →0x82. S→C:Establish/Use respeitam máximo do cliente, sem persistir alias | §3.3.2.3.4, §3.3.4 | T03, W04, W13; histórico R01 |
| Subscription Identifier | 0x0B/VBI | **Não aceito C→S**; permitido S→C, N, 1..268.435.455; até 256 IDs por entrega, repetições do mesmo valor não são eliminadas pelo encoder | §3.3.2.3.8; MQTT-3.3.4-6 | T09, W14 |

Duplicidade de singleton/PFI>1 usa classe `PublishPropertyProtocol` (0x82);
propriedade de outro contexto usa `PublishPropertyMalformed` (0x81). O ID
Subscription Identifier é válido no PUBLISH de servidor, mas proibido no de
cliente; o parser recusa em vez de encaminhar um ID fornecido pelo publicador.

## SUBSCRIBE/UNSUBSCRIBE C→S

Símbolos: ramos de `decode_for_inner` e `parse_subscription_user_property`.
As propriedades de assinatura não são metadados da mensagem publicada.

| Contexto/propriedade | ID/tipo | Multiplicidade, valores e tratamento no XMQR | OASIS | Testes |
|---|---|---|---|---|
| SUBSCRIBE / Subscription Identifier | 0x0B/VBI | 1; 1..268.435.455; associado aos filtros; substituição sem ID armazena ausência; zero fecha, duplicado →0x82, VBI redundante →0x81 | §3.8.2.1.2 | T09, T10, W14, W17 |
| SUBSCRIBE / User Property | 0x26/PAIR | N; UP16; nomes repetidos aceitos, validado e descartado | §3.8.2.1.3 | T10, W15 |
| UNSUBSCRIBE / User Property | 0x26/PAIR | N; UP16; validado e descartado; Subscription Identifier não é permitido neste contexto | §3.10.2.1 | T10, T11, W15 |

SUBACK/UNSUBACK não entram como comando de cliente: headers válidos de pacotes
exclusivos do servidor são recusados antes de interpretar propriedades (T15).
No Local, Retain As Published e Retain Handling são opções, não propriedades;
estão cobertos em `mqtt5_retain_handling_accepts_zero_one_two_and_rejects_reserved_options`,
`mqtt5_shared_filter_requires_group_inner_filter_and_no_local_clear` e
`verify_mqtt5_subscribe_options.py`. Não se confundem com os IDs desta matriz.

## ACKs, AUTH e DISCONNECT C→S

| Contexto/propriedade | ID/tipo | Multiplicidade, valores e tratamento no XMQR | OASIS | Símbolo/testes |
|---|---|---|---|---|
| PUBACK/PUBREC / Reason String | 0x1F/UTF8 | 1; validada e descartada; duplicada →0x82; não se usa para decidir a transação | §3.4.2.2, §3.5.2.2 | `decode_ack_diagnostics`; T12, W16 |
| PUBACK/PUBREC / User Property | 0x26/PAIR | N; nomes repetidos; validada e descartada, sem UP16 | mesmos | `decode_ack_diagnostics`; T12, W16 |
| PUBREL/PUBCOMP / Reason String | 0x1F/UTF8 | 1; validada e descartada; duplicada →0x82 | §3.6.2.2, §3.7.2.2 | `decode_ack_diagnostics`; T12, W16 |
| PUBREL/PUBCOMP / User Property | 0x26/PAIR | N; validada e descartada, sem UP16 | mesmos | `decode_ack_diagnostics`; T12, W16 |
| AUTH / Authentication Method | 0x15/UTF8 | 1 obrigatório no perfil; deve continuar PLAIN negociado no CONNECT; outro método não muda a identidade | §3.15.2.2.2, §4.12 | ramo AUTH + `serve_mqtt`; T13, W06 |
| AUTH / Authentication Data | 0x16/BIN | 1 obrigatório no perfil PLAIN; envelope validado; mesma identidade/principal, geração de segurança vigente; erro de autenticação →DISCONNECT0x86 | §3.15.2.2.3, §4.12 | ramo AUTH + `plain_credentials`; T13, T18, W06 |
| AUTH / Reason String | 0x1F/UTF8 | 1; validada e descartada; duplicada →0x82 | §3.15.2.2.4 | ramo AUTH; T13 |
| AUTH / User Property | 0x26/PAIR | N; validada e descartada, sem UP16 | §3.15.2.2.5 | ramo AUTH; T13, T14 |
| DISCONNECT / Session Expiry Interval | 0x11/U32 | 1; 0..U32_MAX; altera expiração; não pode elevar a partir de CONNECT expiry=0; nunca emitido pelo servidor | §3.14.2.2.2 | ramo DISCONNECT + `serve_mqtt`; T13, W18 |
| DISCONNECT / Reason String | 0x1F/UTF8 | 1; validada e descartada; duplicada →0x82 | §3.14.2.2.3 | ramo DISCONNECT; T13 |
| DISCONNECT / User Property | 0x26/PAIR | N; validada e descartada, sem UP16 | §3.14.2.2.4 | ramo DISCONNECT; T13, T14 |

Os ACKs aceitam formas mínimas e formas com reason/propriedades. Packet ID
zero é 0x82; PUBACK/PUBREC C→S aceitam reasons 00/80/83/87/90/91/97/99 (não
0x10, reservado à emissão pelo servidor); PUBREL/PUBCOMP aceitam 00/92.
AUTH de reautenticação aceita reason 0x19 no perfil, não fluxo genérico 0x18.
DISCONNECT C→S aceita 00/04/80/81/82/83/90/93/94/95/96/97/98/99; somente 00
cancela Will. Propriedade Server Reference não é entrada de cliente suportada.

## Emissão CONNACK e demais pacotes S→C

| Contexto/propriedade | ID/tipo | Emissão atual e limite | OASIS | Símbolo/testes |
|---|---|---|---|---|
| CONNACK / Maximum Packet Size | 0x27/U32 | 65.536 quando cabe; não confundir teto de pacote com payload4.096 | §3.2.2.3.6 | `encode_mqtt5_success_connack`; T02, W03 |
| CONNACK / Receive Maximum | 0x21/U16 | teto de inflight configurado no broker (1..32), se os3bytes adicionais couberem | §3.2.2.3.3 | `append_mqtt5_receive_maximum`; W02 |
| CONNACK / Topic Alias Maximum | 0x22/U16 | 16 quando cabe a variante completa; omitido equivale a0 | §3.2.2.3.8 | `encode_mqtt5_alias_connack`; T03, W03/W04 |
| CONNACK / Shared Subscription Available | 0x2A/B | 1; variante mínima de sucesso tem7bytes completos, não aceita sucesso omitindo a capacidade atual | §3.2.2.3.13 | `encode_mqtt5_shared_available_connack`; T02, W03 |
| CONNACK / Server Keep Alive | 0x13/U16 | quando configuração substitui Keep Alive do cliente; reservado orçamento antes de criar/aceitar sessão | §3.2.2.3.14 | `append_mqtt5_server_keep_alive`; W19 |
| CONNACK / Assigned Client Identifier | 0x12/UTF8 | obrigatório quando broker aceita ClientID vazio; gerado `xmqr-`+32hex (37bytes); precisa caber | §3.2.2.3.7 | `append_mqtt5_assigned_client_id`, `new_assigned_client_id`; T16, W20 |
| CONNACK/AUTH / Authentication Method | 0x15/UTF8 | PLAIN ecoado no sucesso da negociação/reautenticação | §3.2.2.3.17, §3.15.2.2 | `append_mqtt5_plain_method`, `encode_mqtt5_plain_auth_success`; T04, T13, W06 |
| PUBLISH / metadados e Subscription Identifier | IDs da seção PUBLISH | encoder preserva metadados; recalcula expiry; alias por conexão; IDs das assinaturas do destinatário | §3.3.2.3/§3.3.4 | `encode_publish_with_subscription_ids`; T03/T06–T09, W04/W10–W14 |
| PUBACK/PUBREC/PUBREL/PUBCOMP | sem propriedades | sucesso mínimo; negações PUBACK/PUBREC têm reason e PropertyLength0 | §3.4–§3.7 | `encode_*ack`, `encode_mqtt5_puback_reason`, `encode_mqtt5_pubrec_reason`; T12, W16 |
| SUBACK/UNSUBACK | sem propriedades | PropertyLength0, reason por filtro | §3.9/§3.11 | `encode_mqtt5_suback`, `encode_mqtt5_unsuback`; T11, W15 |
| DISCONNECT | sem propriedades | reasons contextuais; resposta suprimida se não cabe no máximo negociado | §3.14, §4.13 | `serve_mqtt`, `write_limited`; W16/W17/W21 |

### Emissões opcionais não utilizadas

Estado **`OPTIONAL_NOT_EMITTED`**, distinto das entradas aceitas:

| Propriedade/ID | Situação atual |
|---|---|
| Response Information0x1A | não emitida, inclusive se RequestResponseInformation=1; emissão é opcional (§3.2.2.3.15) |
| Reason String0x1F, User Property0x26 diagnósticos | não emitidos em CONNACK/ACK/AUTH/DISCONNECT; RequestProblemInformation=0 não causa divulgação desses diagnósticos |
| Authentication Data0x16 de servidor | PLAIN atual termina sem dados de servidor/challenge |
| Session Expiry0x11 no CONNACK | não reescreve o intervalo pedido; não é emitido no DISCONNECT de servidor |
| Maximum QoS0x24, Retain Available0x25, Wildcard Subscription Available0x28, Subscription Identifier Available0x29 | omitidas; defaults de protocolo2/1/1/1, compatíveis com capacidades atuais |
| Server Reference0x1C | sem redirecionamento/construção de razão UseAnotherServer/ServerMoved; não é uma capacidade anunciada |

Não se deduz suporte a uma propriedade de entrada a partir dessa lista; os
contextos de entrada aceitos são somente os discriminados nas tabelas.

## Índice de testes específicos

`Txx` são funções no módulo de testes de codec.rs, salvo caminho indicado.
`Wxx` são scripts em `scripts/`, **disponíveis**, não um registro coletivo PASS.

| Chave | Testes unitários existentes/novos |
|---|---|
| T01 | `mqtt5_rejects_unsupported_properties_without_decoding_as_v311`; `mqtt5_connect_semantic_property_errors_have_protocol_reason` |
| T02 | `mqtt5_maximum_packet_size_connect_property_is_unique_and_nonzero`; `mqtt5_connect_uses_versioned_connack` |
| T03 | `mqtt5_inbound_topic_alias_is_connection_local_and_bounded`; `mqtt5_outbound_topic_alias_vectors`; novo P227D:`mqtt5_unmapped_alias_is_not_an_invalid_numeric_value` |
| T04 | `mqtt5_auth_method_is_refused_distinctly_after_validating_properties`; `mqtt5_plain_connect_requires_initial_data_and_echoes_method_on_success` |
| T05 | `mqtt5_will_delay_connect_vectors`; `mqtt5_will_metadata_preserves_order_and_rejects_invalid_properties` |
| T06 | `mqtt5_publish_format_and_content_type_vectors_and_rejections` |
| T07 | `mqtt5_message_expiry_property_vectors_and_rejections` |
| T08 | `mqtt5_publish_request_properties_roundtrip_and_rejections`; `mqtt5_publish_property_errors_have_contextual_reasons` |
| T09 | `mqtt5_subscription_identifier_codec_accepts_one_and_rejects_invalid_properties`; `mqtt5_publish_and_subscribe_property_contexts_are_separate` |
| T10 | `mqtt5_subscription_user_properties_are_contextual_bounded_and_repeatable`; `mqtt5_subscription_property_errors_have_distinct_reason_classes` |
| T11 | `mqtt5_unsubscribe_has_properties_and_reason_codes` |
| T12 | `mqtt5_puback_accepts_client_rejections_and_strict_diagnostic_properties`; `mqtt5_pubrec_accepts_client_rejections_and_strict_diagnostic_properties`; `mqtt5_accepts_qos2_completion_reasons_and_diagnostics`; `mqtt5_qos_ack_property_errors_have_contextual_reasons` |
| T13 | `mqtt5_reauthentication_auth_requires_method_data_and_valid_reason`; `mqtt5_auth_and_disconnect_property_errors_have_contextual_reasons`; `mqtt5_disconnect_session_expiry_property_is_strict`; `mqtt5_disconnect_accepts_client_reasons_only` |
| T14 | `mqtt5_invalid_utf8_text_is_typed_across_packet_contexts`; `mqtt5_initial_connect_invalid_utf8_uses_connack_reason_and_limit`; `mqtt5_internal_structure_errors_are_typed_across_packet_kinds`; `mqtt5_initial_connect_structure_uses_only_complete_property_boundaries` |
| T15 | `mqtt5_server_only_packets_from_client_are_protocol_errors_before_body`; `mqtt5_reserved_control_type_zero_is_malformed_before_body`; `mqtt5_auth_reserved_flags_are_malformed_before_body`; `mqtt5_qos_ack_reserved_flags_are_malformed_before_body`; `mqtt5_subscription_and_pubrel_reserved_flags_are_malformed_before_body`; `mqtt5_initial_connect_reserved_flags_require_verifiable_version` |
| T16 | `mqtt5_assigned_client_id_is_mandatory_connack_property` |
| T17 | topic.rs: `topic_and_filter_limit_counts_utf8_bytes`; `maximum_depth_and_utf8_are_bounded_without_normalization` |
| T18 | mod.rs: `requires_empty_authorization_id_and_exact_utf8_fields` |
| T19 (novos P227A) | `mqtt5_vbi_canonical_integer_boundaries`; `mqtt5_vbi_rejects_redundant_internal_integer_digits`; `mqtt5_vbi_rejects_noncanonical_established_remaining_length`; `mqtt5_vbi_keeps_legacy_remaining_length_and_canonical_fragments`; `mqtt5_vbi_initial_connect_remaining_length_is_rejected_before_acceptance`; `mqtt5_vbi_property_length_is_strict_in_each_established_context`; `mqtt5_vbi_initial_connect_and_will_property_lengths_never_accept`; `mqtt5_vbi_subscription_identifier_is_canonical` |
| T20 | `packet_quota_counts_complete_header_before_waiting_for_body`; `complete_packet_boundary_survives_fragmentation_and_concatenation`; `publish_payload_boundary_is_preserved_for_all_qos` |

| Chave | Scripts de integração/wire |
|---|---|
| W01 | `verify_mqtt5_sessions.py`, `verify_mqtt5_connect_property_semantic_reason.py` |
| W02 | `verify_mqtt5_receive_maximum.py`, `verify_mqtt5_connack_receive_maximum.py`, `verify_mqtt5_resumed_qos2_quota.py` |
| W03 | `verify_mqtt5_maximum_packet_size.py`, `verify_mqtt5_oversize_disconnect.py` |
| W04 | `verify_mqtt5_topic_alias.py`, `verify_mqtt5_outbound_alias.py` |
| W05 | `verify_mqtt5_connect_property_semantic_reason.py`, `verify_mqtt5_connect_utf8_reason.py` (T01 é o vetor direto dos flags Request*) |
| W06 | `verify_mqtt5_plain_auth.py`, `verify_mqtt5_reauth.py`, `verify_mqtt5_auth_refusal.py`, `verify_phase6_paho_auth.py` |
| W07 | `verify_mqtt5_will_delay.py` |
| W08 | `verify_mqtt5_will_metadata.py` |
| W09 | `verify_mqtt5_will_expiry.py` |
| W10 | `verify_mqtt5_publish_metadata.py` |
| W11 | `verify_mqtt5_message_expiry.py` |
| W12 | `verify_mqtt5_request_properties.py` |
| W13 | `verify_mqtt5_alias_error_disconnect.py`; novo P227D:`verify_phase6_alias_reason.py` (9casos com CONNACK/diagnóstico exatos; histórico R01) |
| W14 | `verify_mqtt5_subscription_identifier.py` |
| W15 | `verify_mqtt5_subscription_user_properties.py`, `verify_mqtt5_subscription_property_disconnect.py` |
| W16 | `verify_mqtt5_negative_puback.py`, `verify_mqtt5_negative_pubrec.py`, `verify_mqtt5_qos2_completion_reasons.py`, `verify_mqtt5_ack_property_reasons.py` |
| W17 (novo P227A) | `verify_phase6_vbi.py` (21vetores, incluindo PropertyLength de nove contextos estabelecidos e CONNECT/Will iniciais) |
| W18 | `verify_mqtt5_disconnect_expiry.py`, `verify_mqtt5_disconnect_with_will.py`, `verify_mqtt5_control_property_reasons.py`, `verify_mqtt5_client_disconnect_reasons.py` |
| W19 | `verify_mqtt5_server_keep_alive.py` |
| W20 | `verify_mqtt5_assigned_client_id.py` |
| W21 | `verify_mqtt5_malformed_utf8.py`, `verify_mqtt5_truncated_fields.py`, `verify_mqtt5_malformed_length_disconnect.py`, `verify_mqtt5_connect_structure.py`, `verify_mqtt5_connect_property_reason.py`, `verify_mqtt5_publish_property_reasons.py` |

## Evidência observada, execução segura e ressalvas

P227A T19: RED no fonte antes da correção2PASS/6FAIL; após correção8/8PASS.
Wire W17 repetido no ELF P227D `mqtt-broker0.42.0`, SHA256
`dca22b2624b7f36175d4e939c640b6f5730220bcc9510580eef9054a6af8ef57`:
**21/21PASS**, cleanupPASS, 3,963s observados. Harness SHA256
`ccc8ecae90ccd18ecc98d27dc8876ad42453a2f2663576f853b6ff38f07fb064`.
Report externo ao repositório: `../.artifacts/p227a-vbi-p227d-candidate-1.json`.
O baseline0.41.0 de20casos2PASS/18FAIL e o GREEN intermediário0.42.0 anterior
permanecem registrados, não substituídos.

P227D T03: RED1FAIL antes do fix; após fix3testesaliasPASS. W13 novo:RED
corrigido5PASS/4FAIL no ELF anterior; **9/9PASS** no ELF P227D acima,2,756s,
cleanupPASS, `../.artifacts/p227d-alias-candidate-2.json`, harnessSHA256
`a9ee09a42bf481a65c1a36177a85a4ac434a0097b25ddad21999647be3de73ed`.
O primeiro candidatoFAIL7/8 foi preservado e explicado no registro P227D,
sem usar erro de fixture como evidência de regressão do runtime.

Exemplo direcionado, após confirmar fonte/ambiente/caches com o coordenador:

```sh
TMPDIR=/var/tmp cargo test --locked -j 1 --lib mqtt5_vbi_ -- --nocapture
python3 scripts/verify_phase6_vbi.py --broker /caminho/ELF-confirmado \
  --state-root /var/tmp --label candidate --report /caminho/novo-report.json
```

W17 aceita caminho explícito, copia o ELF e usa estado/porta privados, env MQTT
limpo, prazos finitos e cleanup. Os scripts históricos W01–W21 frequentemente
usam `target/debug` e fixtures irmãs: executar via runner P227 em clone limpo
e isolado com procedência, **não** apontar à instância/estado do operador nem
supor que um ELF default é a versão da árvore. `verify_phase6_acceptance.py
--phase 6A --report /caminho/novo.json` é o agrupador, não faz build/install.
Interoperabilidade Paho/Mosquitto exige ferramentas/dependências confirmadas;
ferramenta ausente é BLOCKED, não PASS/skip nem autorização para instalar.

Ressalvas e trabalho restante, sem modificar checklists globais:

1. **R01 — corrigida no recorte P227D:** `TopicAliasUnmapped` distingue lookup
   ausente do valor zero/excessivo; serve_mqtt emite0x82 conforme §3.3.4 caso3a.
   Zero/excesso continuam0x94, inclusive se CONNACK omite TopicAliasMaximum e
   seu default é0. W13 histórico foi corrigido; novos9vetores estão verdes.
   Não generalizar esse resultado a outros motivos de erro ou certificação.
2. T05 verifica metadados/duplicidades Will, mas não enumera cada fronteira
   exata de UP16/ContentType/CorrelationData nesse ramo. T08/T10 testam vários
   excessos, não todas as combinações exatas2048/2049 e256/257 em ambos sentidos.
   Tetos constam do código; não são anunciados como cobertura de fronteira total.
3. Nem toda recusa semântica/local tem tipo diagnóstico dedicado: por exemplo
   SubscriptionIdentifier0, TopicName vazio sem alias e excesso de metadados
   fecham por erro genérico. Não afirmar emissão universal de0x81/0x82/0x95.
4. W17 é open-labTCP sintético. Não comprova TLS/mTLS, durabilidade, fairness,
   todas as combinações QoS, todos os estados de AUTH ou cada plataforma.
5. Full fmt/test/Clippy, regressão3.1.1, dois clientes externos, campanhas de
   crash e demais gates finais são consolidados pelo coordenador com hashes
   e resultados próprios. O status geral6A–6D não muda por criar esta tabela.

Material autoral MIT; referências OASIS permanecem links à fonte oficial.
