# Aceite da fase 6 de MQTT 5

Estado em 18 de outubro de 2026: **fase 6 aceita no contrato finito M01–M10**.
A CI integrada passou em 69/69 fixtures nas fontes abaixo. O broker 0.43.0
foi publicado com pacote, imagens e evidências conferidos por SHA remoto.

Este aceite cobre o contrato M01–M10 do [plano de paridade](plano-paridade-mosquitto.md),
não cada extensão opcional do protocolo ou equivalência integral a Mosquitto.
A [matriz de propriedades e contextos](conformance/mqtt5-property-matrix.md)
discrimina entradas, emissões, quotas e escolhas opcionais.

## Fontes e entregas

| Componente | Fonte selecionada | Situação |
| --- | --- | --- |
| Broker e admin legado 0.43.0 | `db472bc64558bf0e376a902b7780a259247c5149` | [CI padrão PASS](https://github.com/licodevone/xmqr/actions/runs/39164202189); [CI integrada SUCCESS](https://github.com/licodevone/xmqr/actions/runs/39164217059); [prerelease com 12 anexos verificados](https://github.com/licodevone/xmqr/releases/tag/v0.43.0) |
| Client 0.40.0 | `501cde2ffbae6985f033ed8be60d9ad6dd8c18c4` | [Publicado com pacote e imagem](https://github.com/licodevone/xmqr-client/releases/tag/v0.40.0); SHA efetivamente compilado e exercitado na CI integrada |
| Admin independente 0.11.0 | `4483a356196db93f99340bc7aa3b3cabfc4af810` | [Publicado](https://github.com/licodevone/xmqr-admin/releases/tag/v0.11.0); [CI exata PASS](https://github.com/licodevone/xmqr-admin/actions/runs/39143572778), compatibilidade A21 e distribuição A22 verificadas |

O client0.40.0 mantém o journal inbound C129/C131 e acrescenta a bridge
distribuída porC135; o aceite global da fase8 continua separado. O admin
fixa o core público `ba6ef50`; o diff
de `src`, Cargo e Docker até o candidato broker selecionado é vazio. Igualdade
de versão, isoladamente, não prova equivalência das fontes.

## Critérios 6A–6D

| Parte | Requisitos | Evidência funcional | Resultado |
| --- | --- | --- | --- |
| 6A | M01/M02: negociação, codec contextual, propriedades, limites, motivos e coexistência 3.1.1 | 32 fixtures 6A; VBI 21, aliasReason 9, fronteiras P227I e peers Mosquitto/Paho | PASS na CI final |
| 6B | M03/M04: sessões, expiração, Will Delay, migração e obrigações QoS duráveis | 13 fixtures 6B, incluindo crash 12; journal inbound 21, compatibilidade 6 e migração real v1→v2; A21 com estado15 real→16; clock/identidade P227E nos testes Rust | PASS na CI final |
| 6C | M05/M06/M07: negociação bilateral, backlog, aliases e metadados duráveis | 12 fixtures 6C: Receive Maximum/Maximum Packet Size, controle com quota esgotada, QoS0/1/2, reset de alias, Paho e metadados | PASS na CI final |
| 6D | M08/M09 e decisão M10: opções/IDs, shared/failure/fairness e AUTH | 12 fixtures 6D: assinaturas persistentes, redistribuição QoS1, shared/Will 3, PLAIN TLS/mTLS e reauth explícita | PASS na CI final |

Os números representam grupos de teste que podem se sobrepor. Não somar
unitários filtrados, repetições ou casos internos ao total de 69 fixtures.

Eall8 local com client0.38.0: 198,043s, fontes db472bc/fca6fc8/4483a35 limpas e verificações
de fonte, binários e legados inalterados. SHA256 do relatório:
`67a45f7bd68f56d47ebbb9b76654cb534d42e7cc19c636956ab35db4645a7f5e`.
Broker/admin legado usam os ELFs extraídos do pacote CI39164202189; admin
independente usa o ELF do pacote final4483. Não são builds debug locais.

A CI final executou 311 testes Rust do broker, 184 do client0.40.0 e 27 do
admin0.11.0, além de fmt/Clippy/builds/inventários e 22 contratos do executor.
As seis campanhas fuzz opt-in ignoradas pelo gate comum do broker continuam
assim identificadas; não são apresentadas como executadas por este aceite.
Campanha integrada: 169,757s, 69PASS/0FAIL/0BLOCKED e três verificações
unchanged=true. Os13JSON foram baixados, parseados e conferidos contra
fontes, helper e manifesto ELF; SHA256 de `phase6.json`:
`fe2757b81cda6f77a98713e9944bcae2500c7eaaab5bbf4074de34b3ff4f1ec5`.
Mosquitto2.0.22, Paho2.1.0 e OpenSSL3.5.5 são os peers/ferramentas observados.

## Rastreabilidade M01–M10

Os nomes abaixo são fixtures do registro `scripts/verify_phase6_acceptance.py`,
executadas em recursos privados; não são comandos para uma instância instalada.

| ID | Provas principais |
| --- | --- |
| M01 | `verify_mqtt5_cross`, `verify_paho_mqtt5` e fixtures 6A de CONNECT, flags, UTF-8, comprimentos e motivos |
| M02 | Matriz por contexto, `verify_phase6_vbi`, `verify_phase6_alias_reason` e nove grupos unitários P227I |
| M03 | `verify_mqtt5_sessions`, `verify_mqtt5_disconnect_expiry`; journal inbound, compatibilidade e migração real do client |
| M04 | `verify_mqtt5_message_expiry`, `will_delay`, `will_expiry`, `verify_phase6_crash_matrix`, P227E e `verify_core_v16_expiry` do admin |
| M05 | `verify_mqtt5_receive_maximum`, `connack_receive_maximum`, `maximum_packet_size`, `resumed_qos2_quota` e `verify_phase6_control_progress` |
| M06 | `verify_mqtt5_topic_alias`, `outbound_alias`, `verify_phase6_alias_reason` e `verify_phase6_paho_alias` |
| M07 | `verify_mqtt5_publish_metadata`, `request_properties`, `will_metadata` e fronteiras P227I |
| M08 | `verify_mqtt5_retain_handling`, `subscribe_options`, `subscription_identifier` e `subscription_user_properties` |
| M09 | `verify_mqtt5_shared_live`, `shared_durable`, `shared_qos1_reassignment` e `verify_phase6_shared_will` |
| M10 | `verify_mqtt5_plain_auth`, `reauth`, `auth_refusal` e `verify_phase6_paho_auth`; [decisão AUTH](architecture/adr-0007-mqtt5-auth-scope.md) |

## Recuperação e distribuição

O broker 0.43.0 lê documentos1–15 e grava16, sem inventar intervalo original
legado. Mensagens com Message Expiry conservam seu intervalo original, e
obrigações QoS1/2 recebem identidade durável. Prepared e MayHaveSent têm
decisões de expiração distintas. Os testes de
descarte atrasado verificam identidade/estágio, não apenas Packet Identifier.

Antes da migração, preserve backup privado do formato15 com o broker parado.
Voltar ao broker antigo que lê formato15 (por exemplo, 0.42.0) não converte
estado16: restaure o backup anterior em destino novo.
O marcador de perfil é metadado operacional separado e não é incluído pelo
backup do snapshot/WAL. O lifecycle P228B testa também a recusa do restore
não marcado, antes de restaurar separadamente o marcador original.

O pacote é Ubuntu26.04 amd64. As imagens usam binários compilados para
Debian Bookworm e não recebem o `.deb` Ubuntu. Tags publicadas são imutáveis;
não se move `latest`. O pacote0.43.0 e as imagens numeradas passaram ciclo
descartável e conferência de digest remoto. Os 12 anexos da release incluem
`SHA256SUMS`, manifesto, inventário, notices originais e os 13 JSON de
aceite; tamanho e SHA-256 remotos coincidem com os arquivos locais. Evidências
e falhas históricas permanecem nos registros
[P227](../prompts/registros/P227-fechamento-integrado-fase6.md),
[P228](../prompts/registros/P228-release-0.43.0-state-v16.md) e
[P228B](../prompts/registros/P228-distribution-artifacts.md).

## Limites do aceite

- PLAIN inicial exige TLS/mTLS; reautenticação é explícita e da mesma
  identidade. Desafios arbitrários e reautenticação periódica não são oferecidos.
  Paho comprova autenticação inicial, não reauth externa.
- O adapter do harness Paho resolve aliases no callback; isso não é resolução
  nativa da biblioteca. Mosquitto2.0.22 como receptor de alias compacto mantém
  a incompatibilidade reproduzida, não uma homologação dessa direção.
- O publisher do client é serial. O journal inbound é opt-in Linux/WSL;
  stdout e aplicação não formam uma transação, portanto pode haver duplicação.
- Fairness compartilhada vale durante a vida do processo. SIGKILL e testes
  finitos não comprovam queda de energia, SLA, produção ou certificação integral.

Código próprio MIT; dependências e imagens-base conservam suas licenças e
notices originais. Este trabalho não instala pacotes nem migra estado do operador.
