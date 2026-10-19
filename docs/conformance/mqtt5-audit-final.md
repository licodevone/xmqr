# Parecer final — auditoria MQTT 5 do XMQR

**Auditoria P232 concluída com achados em 18/10/2026. Conformidade global não
demonstrada; o client tem cinco desvios obrigatórios reproduzidos.** Isto é
um parecer técnico de escopo delimitado, não certificação externa, aprovação
de produção ou garantia de ausência de outros defeitos.

O broker manteve seus resultados positivos e não teve uma violação MUST
reproduzida nesta campanha. Isso não equivale a conformidade integral:
persistem lacunas de evidência. O resultado do client não deve ser atribuído
automaticamente ao broker, e o aceite anterior da fase 6 não é revogado nem
transformado em certificado.

## Escopo examinado e método

Fonte: [OASIS MQTT 5.0 OS de 07/03/2019](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html),
com hash registrado no [resumo de evidências](mqtt5-audit-evidence.json).
Foram classificados **252 identificadores literais para cada um dos dois
papéis**, totalizando 504 avaliações, mais **37 revisões de regras não
numeradas por seção**. Capítulos normativos 1, 2, 3, 4, 6 e critérios de
conformidade do 7 examinados; o capítulo 5 é orientação não normativa.

Os 252 IDs não representam 252 obrigações únicas nem um denominador para
porcentagem de conformidade. Foram preservadas as divergências de IDs e de
resumo conhecidas no HTML; o texto principal prevaleceu sobre o apêndice B.
Regras condicionais, recursos opcionais e deveres exclusivos de um papel
foram separados. O inventário mecânico P231 continua imutável/UNREVIEWED;
as avaliações semânticas estão nos ledgers abaixo, não dentro do inventário.

| Partição | IDs | Registro completo |
| --- | ---: | --- |
| CONNECT, CONNACK e AUTH | 87 | [connect-auth](mqtt5-audit-connect-auth.json) |
| PUBLISH, confirmações, assinaturas, tópicos e shared | 101 | [publish-subscribe](mqtt5-audit-publish-subscribe.json) |
| Sessões, QoS, retransmissão, ordem, controle e erros | 48 | [session-flows](mqtt5-audit-session-flows.json) |
| Representação, framing, identificadores e WebSocket | 16 | [framing-transport](mqtt5-audit-framing-transport.json) |

Cada ID tem resumo autoral, força normativa, aplicabilidade por papel,
justificativa, código, testes existentes e evidência quando disponível.
`SUPPORTED_BY_INSPECTION` significa código examinado: não é PASS dinâmico.
`EVIDENCE_GAP` registra a insuficiência em vez de presumir aprovação.
`NOT_APPLICABLE` tem justificativa de papel/condição; não é uma forma de
ignorar implementação ausente. O validador verifica accounting e referências,
não a verdade semântica dos julgamentos nem autenticidade de relatório externo.

## Fontes e binários

- Broker auditado: `4bfac0722074c7a1f704f335d2d1b558e68e3d6b`, versão 0.43.0.
  O ELF usado veio do pacote publicado de fonte `db472bc`; comparação de
  `src`, Cargo.toml, Cargo.lock e Dockerfile até o snapshot auditado foi vazia.
- Client auditado: `e03c5a46cfb33666896eb710892cf46e3c40ee38`. Testes usaram o
  ELF do `.deb` publicado 0.41.0, fonte `1d60d38`, com SHA-256 conferido.
  CLI, vendor e manifests não mudaram entre as duas fontes. Alterações
  posteriores de `mqtt-bridge.rs`/`bridge_journal.rs` foram explicitamente
  excluídas dessa igualdade; a bridge inteira não foi homologada por inferência.
- Admin 0.11.0 é contexto operacional, não outro endpoint MQTT. A compatibilidade
  administrativa anterior não substitui conformidade do broker/client.

Os hashes completos, diferenças consideradas e fontes de cada campanha estão
no [JSON de evidências](mqtt5-audit-evidence.json). A CI integrada histórica
[39164217059](https://github.com/licodevone/xmqr/actions/runs/39164217059) continua
com seus 69 cenários e peers exatos antigos; não foi atribuída ao client atual
como execução nova. Não foi feito rebuild de Rust nesta auditoria documental
e de probes: foram executados os binários publicados, sem alterar o runtime.

## Resultado da classificação

| Situação da revisão numerada | Broker | Client |
| --- | ---: | ---: |
| Suporte por inspeção, não PASS dinâmico | 220 | 115 |
| Evidência insuficiente | 2 | 18 |
| Desvio obrigatório identificado | 0 | 5 |
| Não aplicável ao papel/condição justificada | 30 | 114 |

Essas colunas somam IDs classificados, não testes independentes. As 37
revisões por seção e 20 registros de achados incluem sobreposições e
recomendações: **não significam 20 bugs distintos**. Não há ID numerado sem
classificação no escopo; isso não demonstra exaustividade de todas as entradas,
interações ou possíveis obrigações não numeradas.

## Cinco correções obrigatórias prioritárias no client

Os cinco casos abaixo falharam no wire, com controles positivos funcionando:

| Prioridade | Comportamento observado | Requisito |
| --- | --- | --- |
| Alta | Uma mesma transação PUBLISH QoS2 foi exibida duas vezes antes de PUBREL no modo comum | `MQTT-4.3.3-10` |
| Alta | PUBREL repetido após conclusão não recebeu novo PUBCOMP; a CLI encerrou com erro | `MQTT-4.3.3-11` |
| Alta | Publicou QoS1 apesar de CONNACK anunciar Maximum QoS0 | `MQTT-3.2.2-11` |
| Alta | Publicou com RETAIN apesar de Retain Available0 | `MQTT-3.2.2-14` |
| Média | Nova invocação sem estado local prosseguiu com Session Present1, Clean Start=false | `MQTT-3.2.2-4` |

O journal opcional tem caminhos diferentes para QoS2; não estender a falha
do modo comum a todos os modos, nem aceitar que a existência do journal torne
o modo padrão automaticamente correto. Correções precisam preservar as
garantias já exercitadas, inclusive durabilidade antes dos ACKs pertinentes.

## Recomendações e lacunas, separadas de MUST

Quatro probes adicionais confirmaram aceitação de pacote do servidor falso
com NUL no tópico, NUL em User Property, VBI redundante ou flags reservadas
de PUBACK inválidas. São lacunas de validação de recepção a corrigir ou
justificar; o parágrafo Client não numerado de §4.13.1 usa **SHOULD**, não
o MUST de fechamento imposto ao Server. O servidor falso produziu bytes
inválidos: esses testes não demonstram emissão inválida pelo client.
Não existe `MQTT-4.13.1-2` na fonte; não usar esse identificador.

No broker, fechamento sem diagnóstico em Subscription Identifier0, tópico
vazio sem alias e takeover foi observado. Os três fechamentos obrigatórios
passaram; a nova conexão de takeover respondeu PING. A ausência de 0x8E não
foi classificada como violação MUST comprovada: a interpretação da notificação
e eventual melhoria permanecem separadas do fechamento obrigatório.

Também permanecem explícitas:

- Quota de destino/decisão de encaminhamento antes de PUBREC no broker:
  candidato de evidência insuficiente, não desvio reproduzido.
- Política recomendada sobre tópicos `$`: inspeção e justificativa adicional,
  sem transformar geração de `$SYS` em capacidade obrigatória.
- Perigos de DUP, aliases e janelas em reconexão na biblioteca rumqttc:
  mecanismos estáticos localizados, mas sem caminho atingível demonstrado
  nos fluxos CLI examinados. Não contados como falhas comprovadas do produto.
- Recepção de texto de servidor WS pelo adaptador do client, namespace de
  identificadores e retenção/validação em todos os modos de sessão:
  ampliação de evidência conforme cada registro, sem PASS presumido.

Ausência de métodos opcionais AUTH diferentes de PLAIN não foi tratada como
falha automática. O mecanismo oferecido é que precisa cumprir seu contrato.

## Execuções novas e controles

| Campanha | Resultado observado | Interpretação |
| --- | --- | --- |
| Client, relatório final6 | 12 cenários: 3PASS, 9FAIL, 0BLOCKED | 2 controles canônicos + rejeição UTF-8 malformado PASS; 5 falhas MUST e 4 recomendações de recepção FAIL |
| Broker VBI | 21/21PASS | Vetores definidos, não cada combinação MQTT |
| Broker aliases | 9/9PASS | Mapeamento, reset e diagnósticos definidos |
| Broker fechamentos | 3/3PASS, nenhum diagnóstico observado | Separação factual entre fechar e enviar diagnóstico |

Campanhas loopback/Ubuntu-26.04 WSL, estado nativo privado em `/var/tmp`,
portas efêmeras, prazos e cleanup; binários conferidos antes/depois.
Não houve contato com broker operacional ou uso de credenciais reais.
Os relatórios anteriores1–5 foram mantidos, inclusive o primeiro erro de
harness SUBACK/QoS. Seus resultados não foram promovidos retroativamente.

Reproduzir as verificações offline na raiz do broker, com o client auditado
na pasta irmã para resolver referências:

```text
python scripts/test_mqtt5_normative_inventory.py
python scripts/test_mqtt5_audit_ledger.py
python scripts/mqtt5_audit_ledger.py
```

Para probes, usar explicitamente ELFs de fonte/hash conhecidos, relatórios
novos e ambiente Linux isolado. `verify_p232_client_wire.py` retorna exit1
quando confirma as falhas: não é esperado transformá-lo em PASS sem corrigir
o produto ou justificar uma recomendação, e nunca enfraquecendo o oráculo.
Testes do validador são testes de accounting, não testes de protocolo.

## Revisão independente e encerramento

Sol/high executou as três partições de revisão semântica. Luna/high revisou
os contratos mecânicos e a observabilidade dos probes. Astra/high revisou
os 252 resumos, 37 entradas por seção, achados e amostras dirigidas da norma
e código, corrigindo interpretações de takeover, alcançabilidade na biblioteca
e MUST/SHOULD. Não foi uma segunda auditoria independente exaustiva de cada
implementação nem uma execução de testes por esses revisores.

**Encerrada esta auditoria com parecer negativo para declaração integral do
client e inconclusivo para declaração integral do broker.** As pendências
agora são ações de correção/validação identificadas, não revisão numerada
ocultamente deixada por fazer. Próximo trabalho autorizado deve começar pelos
cinco desvios do client, com prompts próprios e regressões; só uma entrega
funcional aceita justifica nova versão, tag, release, `.deb` e Docker.

Nenhum runtime foi alterado, portanto não se criou tag/release artificial.
Tags e releases anteriores, MIT autoral e licenças de terceiros foram
preservadas. Os registros são material de auditoria; não modificam as
licenças da norma OASIS ou os contratos operacionais fora do escopo.

Ver [prompt P232](../../prompts/broker/232-concluir-auditoria-mqtt5.md) e
[registro de execução](../../prompts/registros/P232-concluir-auditoria-mqtt5.md).
