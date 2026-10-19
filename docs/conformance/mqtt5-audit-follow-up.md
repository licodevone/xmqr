# Acompanhamento das correções MQTT 5 após P232

Atualizado em 19/10/2026, por P233. O [parecer P232](mqtt5-audit-final.md)
e seus ledgers conservam os resultados das fontes auditadas naquela campanha.
Este acompanhamento registra evidência posterior; não muda FAILs históricos.

## Correções verificadas

| Achado de P232 | Evidência posterior | Distribuição |
| --- | --- | --- |
| Maximum QoS e Retain Available, MQTT-3.2.2-11/-14 | C140 e controles nos 42 cenários C140–C142 | Client 0.42.0 |
| Session Present sem estado local, MQTT-3.2.2-4 | C141 recusa a sessão; modos com estado preservados | Client 0.42.0 |
| Entrega repetida QoS 2 e PUBREL repetido, MQTT-4.3.3-10/-11 | C142, controles e regressões nos ELFs do pacote e imagem | Client 0.42.0 |
| NUL recebido em tópico/User Property, VBI redundante e flags reservadas | C144: 14/14 na CI debug/pacote e na imagem; P232 original 12/12 no pacote; cinco jobs CI C146 PASS | Client 0.42.1, fonte `db844a0` |
| Texto recebido como dados WS/WSS, MQTT-6.0.0-1 | P234: 12/12 local e na CI específica, mesmo ELF do pacote 0.42.1; controles binários e rejeição rápida de texto em MQTT 3.1.1/5 | Comportamento já existente demonstrado, sem alterar runtime |

[Aceite C143](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C143-five-audit-fixes.md):
release 0.42.0 da fonte `e0e553c3328839177c293870a6d12291c0099d19`,
[CI exata](https://github.com/licodevone/xmqr-client/actions/runs/39183999929)
com cinco jobs PASS. Pacote/imagem e seis anexos remotos conferidos; o mesmo
marco distribui bridge 0.4.0/C139. Broker/admin mantêm 0.43.0/0.11.0.

[Registro C144](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C144-mqtt5-receive-validation.md)
e [CI `25c2e8a`](https://github.com/licodevone/xmqr-client/actions/runs/39194165930)
identificam a execução posterior. O relatório local anterior ao commit conserva
seus hashes próprios; não se apresenta como executável da release 0.42.0.
C145 retira artefatos de compilação do índice sem apagar arquivos locais.

[Publicação C146](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C146-release-0.42.1.md):
client 0.42.1, fonte `db844a0808dfa82e436e5b0fe960d66536df4703`,
[CI](https://github.com/licodevone/xmqr-client/actions/runs/39257417702) com cinco
jobs PASS. Tag/pacote/imagem e seis anexos remotos conferidos. A tentativa
local de lifecycle excedeu 180s e continua FAIL_TIMEOUT; o mesmo ciclo passou
na CI. Nenhuma tag antiga ou latest foi movida.

## Evidência ainda necessária

As duas lacunas de evidência do broker e as 18 do client no ledger P232 são
registros históricos, não 20 defeitos comprovados. Alguns casos de recepção
foram cobertos por C144; isso não encerra automaticamente cada obrigação de
emissão, todos os campos, todas as sessões ou as interações da biblioteca.

O [teste P234](../../prompts/registros/P234-quadros-websocket-client.md) já
demonstrou localmente e na [CI específica](https://github.com/licodevone/xmqr/actions/runs/39259711349)
o fechamento por texto do servidor WS/WSS. O histórico
P232 permanece como EVIDENCE_GAP daquela campanha. Evidência nova vale para os
12 casos definidos, sem cobrir todos os frames malformados.

Próximos probes independentes:

- Broker: ownership QoS 2 e quota de destinatário antes/depois de PUBREC,
  MQTT-4.5.0-1/§4.4, incluindo retomada e ausência de perda silenciosa.
- Client: interações de ACKs/controles com quota cheia, aliases/DUP após
  reconnect, namespace de PIDs e estado de sessão nos modos efetivamente
  alcançáveis. Hipótese estática na biblioteca não é desvio reproduzido da CLI.
- Broker: explicitar a política recomendada para tópicos iniciados por `$`,
  separando wildcard obrigatório, autorização e a decisão de não gerar `$SYS`.

Cada novo resultado exige fonte/binário, oráculo, controles e relatório próprios.
Não há declaração de conformidade integral, certificação externa ou produção.
As fases 6/7 mantêm seus aceites finitos; a fase 8 e a distribuição ampliada
do plano continuam abertas.
