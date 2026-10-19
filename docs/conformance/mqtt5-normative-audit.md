# Auditoria normativa MQTT 5 — P231

Estado atual: **auditoria P232 concluída com achados**, conforme o
[parecer final](mqtt5-audit-final.md). Conformidade integral não demonstrada.
Este arquivo preserva o inventário/triagem inicial P231; não é certificado.
O [aceite experimental da fase 6](../phase6-acceptance.md) continua válido no
seu recorte, distinto da auditoria normativa.

## Base reproduzível

Fonte: [OASIS MQTT 5.0 OS, 07 March 2019](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
O catálogo [JSON](mqtt5-normative-audit.json) registra **252 IDs distintos** em
**501 referências numeradas**. Por capítulo: 1=5, 2=7, 3=175, 4=61 e 6=4.
Isso **não** conta obrigações MUST aplicáveis ao broker nem mede cobertura.
Há referências repetidas no corpo/apêndice, condições, recomendações e regras
para papéis diferentes. Regras obrigatórias também podem estar em texto não
numerado. Não usar `252` como denominador de porcentagem de conformidade.

Fonte baixada nesta execução: 1.436.047 bytes, charset declarado windows-1252,
SHA-256 `41116bcf54bc9b9ee72a425406293efda60fb40741e7d1512b87f51a46fa499c`.
O catálogo mantém literalmente tanto `MQTT-4.2.0-1` quanto `MQTT-4.2-1`,
presentes na fonte; não os une nem corrige silenciosamente. Esses dois IDs e
`MQTT-3.2.2-8` aparecem uma vez cada; os outros aparecem duas vezes.
Essa discrepância precisa de leitura humana antes de contar obrigações.
O corpo também contém o token truncado `T-3.2.2-8]`, que a extração estrita não
transforma automaticamente em requisito. Em `MQTT-3.3.1-10`, a condição sobre
assinatura preexistente está invertida no apêndice em relação ao corpo. O
apêndice B é resumo não normativo: para decidir comportamento, consultar o
texto principal e §7, não usar o resumo como oráculo independente.

O extrator indexa referências visíveis entre colchetes, não entende a semântica
normativa nem comprova autenticidade apenas por reconhecer título/data. A URL,
o download oficial e o hash fixam a procedência observada. Mudança do HTML,
inclusive editorial, pode mudar o hash e exige revisão antes de regenerar.

O HTML integral fica fora do Git; não foi copiado para o pacote. O script e
as análises autorais permanecem MIT; a norma e marcas OASIS mantêm seus
direitos próprios, não são relicenciadas pelo XMQR.

## Papéis e critério de conclusão

Conforme §7.1.1/§7.1.2, broker e client precisam de avaliações separadas.
O `xmqr-admin` não é um terceiro broker MQTT: ações administrativas, backup
e painel têm contratos próprios; seu teste não substitui conformance do wire.

Cada entrada começa `broker=UNREVIEWED`, `client=UNREVIEWED`. Estes estados
significam que **este inventário ainda não julgou a regra**, não que o produto
não a implemente. O JSON é gerado e não deve ser editado para inserir PASS.
Os ledgers semânticos separados P232, ligados no parecer final, classificam
todos os IDs; não confundir o template mecânico com revisão ainda aberta.
O contrato de registro por papel é:

1. Requisito/§, incluindo cláusulas não numeradas, força MUST/SHOULD/MAY,
   condições e justificativa de aplicabilidade ou não aplicabilidade.
2. Commit exato, símbolo/caminho do código, teste e cenários positivos/negativos.
3. Evidência executada: fonte/binário, comando, ambiente, relatório e resultado.
   Nome de teste ou comentário com ID não constitui PASS.
4. Julgamento revisado: satisfeito no recorte demonstrado, desvio reproduzido,
   evidência insuficiente ou não aplicável com justificativa.

Recursos opcionais ausentes não são automaticamente desvio; os que são
oferecidos precisam respeitar as regras pertinentes. Recomendações SHOULD
merecem avaliação/justificativa, mesmo quando não há violação de um MUST.
Modelos ajudam a revisar; nenhum deles emite certificação externa.

## Triagem inicial — inspeção, sem novos testes do broker

Base de código: `76d3cbdf48b8c6ab1ac74b29fc7bb00eb16ad1ac`, runtime 0.43.0.
A matriz [por propriedade](mqtt5-property-matrix.md) apontava três recusas
genéricas. Leitura de §4.13.1 distingue encerramento obrigatório de envio
recomendado de DISCONNECT em conexão estabelecida. Não marcar a regra inteira
como aprovada a partir destes poucos caminhos.

| Caso | Evidência estática e teste existente (não reexecutado) | Resultado da triagem |
| --- | --- | --- |
| Subscription Identifier zero em SUBSCRIBE, §3.8.2.1.2 | `src/mqtt/codec.rs:927` retorna erro genérico; `src/mqtt/mod.rs:534` propaga erro. Unitário `mqtt5_subscription_identifier_codec_accepts_one_and_rejects_invalid_properties`; fixture `scripts/verify_mqtt5_subscription_identifier.py` | Protocol Error; falta diagnóstico específico recomendado. A ausência de DISCONNECT sozinha não prova violação do fechamento MUST `MQTT-4.13.1-1`. Reexecução wire e justificativa SHOULD pendentes. |
| Topic Name vazio sem alias, §3.3.2.1/§3.3.4 | `src/mqtt/codec.rs:322`, mesmo caminho genérico. Unitário `mqtt5_inbound_topic_alias_is_connection_local_and_bounded` rejeita. Não confundir com alias válido porém não mapeado, já tipado/testado por P227D | Mesmo cuidado MUST/SHOULD; diagnóstico recomendado `0x82` permanece melhoria candidata. Nenhum novo desvio obrigatório reproduzido nesta fatia. |
| Metadados acima de quota local | `src/mqtt/codec.rs:1086` e helper `parse_subscription_user_property`; testes P227I em `codec.rs:4511` e seguintes verificam limites | Quota de metadados não é automaticamente Maximum Packet Size nem justifica universalmente `0x95`. Classificar cada política por §4.13.2 antes de definir resposta. Evidência wire específica pendente. |

§4.13.2/`MQTT-4.13.2-1` diferencia restrições locais, inclusive encerramento
associado a razão >=0x80 mesmo quando a resposta não é enviada. Em CONNECT
inicial, respeitar também `MQTT-3.14.0-1`: não enviar DISCONNECT antes de
CONNACK bem-sucedido. Não aplicar cegamente a mesma resposta a todos os contextos.

Esta triagem não aprova universalmente os fechamentos ou as quotas. A passagem
de erro precisa ser acompanhada até o encerramento do transporte e validada
no wire. Não se demonstrou novo FAIL funcional; também não se produziu novo
PASS de protocolo. Testes anteriores continuam com suas fontes e limites.
A leitura acompanhou a propagação até `src/mqtt/mod.rs:673` (cleanup) e
`serve_connection`, em `src/mqtt/mod.rs:111`, que chama shutdown; isso é
evidência de código, não uma nova observação de rede.

## Reproduzir a ferramenta

Baixe a fonte oficial para um arquivo local **fora do repositório**. Na raiz
do broker, com Python 3.11 ou superior:

```text
python scripts/test_mqtt5_normative_inventory.py
python scripts/mqtt5_normative_inventory.py --source CAMINHO_HTML --check docs/conformance/mqtt5-normative-audit.json
```

Para uma fonte revisada, `--output NOVO_JSON` cria arquivo novo exclusivamente:
não sobrescreve catálogo existente. Compare a mudança antes de adotá-la.
`CHECK_PASS` significa somente que o inventário coincide com a extração daquela
fonte; não significa aprovação normativa MQTT 5. A ferramenta não baixa dados,
compila binários, instala dependências, inicia broker nem publica artefatos.
A CI `MQTT5 inventory contracts (not protocol conformance)` roda contratos
sintéticos e consistência interna do catálogo. Ela não baixa a fonte nem
substitui a comparação `--check` com o HTML oficial observado.

## Gestão de modelos e histórico da continuação

Nesta fatia Luna/high localizou evidências e Sol/high revisou a interpretação
normativa. O coordenador integrou as conclusões. A seleção foi feita na criação
dos subagentes, não por troca do modelo principal ou configuração global.

O recorte proposto originalmente (capítulos1/2, regras não numeradas e depois
sessão/QoS/AUTH) foi executado com as demais seções em P232. O parecer final
separa cinco desvios obrigatórios do client, recomendações de recepção,
lacunas de evidência e suporte por inspeção. A continuidade é corrigir e
validar os achados por prompts próprios, não recontar IDs como certificado.

Prompt e resultados reais: [P231](../../prompts/broker/231-auditoria-normativa-mqtt5.md)
e [registro](../../prompts/registros/P231-auditoria-normativa-mqtt5.md).
