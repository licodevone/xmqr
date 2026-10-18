# P195 v1 — UTF-8 malformado após CONNACK MQTT 5

Estado de entrada: `main` limpo em `6a55edc`, broker/admin legado 0.34.0, estado durável v15. P194 aceito; fase 6A aberta. O `Cursor::text` já recusa bytes UTF-8 malformados e escalares proibidos, mas o erro não é tipado e após CONNACK MQTT 5 fecha sem DISCONNECT de diagnóstico.

Objetivo observável: se um campo MQTT UTF-8 lido após CONNACK contiver codificação inválida ou U+0000, o broker tenta DISCONNECT `0x81` (Malformed Packet) e fecha a conexão antes de alterar assinatura, publicação, retained ou obrigação QoS. Aplique a classificação aos textos de PUBLISH, SUBSCRIBE, UNSUBSCRIBE, AUTH, DISCONNECT e diagnósticos de ACKs lidos pelo mesmo cursor. Preserve o Will da conexão original. MQTT 3.1.1 continua fechando sem DISCONNECT MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §1.5.4 MQTT-1.5.4-1/-2 (UTF-8 bem formado e U+0000), §1.5.7 MQTT-1.5.7-1 (pares de strings) e §4.13.1 (Malformed Packet `0x81` e encerramento). O filtro atual de outros caracteres de controle/não caracteres fica preservado como política local; não afirmar que todos têm a mesma obrigação normativa.

Escopo: erro tipado no leitor de texto, propagação pelos parsers que o usam, motivo no loop pós-CONNACK, testes unitários por contexto e TCP para rejeição, Will, ausência de efeitos e regressão MQTT 3.1.1; CI, conformidade/plano e registro. Não expandir parsing de propriedades, aceitar novos caracteres, mudar quotas, client/admin, estado v15 ou versionamento. Erros de texto em CONNECT inicial/Will continuam lacuna separada porque a versão e o Maximum Packet Size precisam ser tratados antes da resposta CONNACK.

Invariantes: não classificar truncamento de comprimento binário nem falhas de tópico/ACL como erro UTF-8; não depender de comparação com texto de erro. Respeitar Maximum Packet Size do destinatário, tolerar falha ao enviar DISCONNECT e fechar. Não alterar o fluxo de sucesso.

Aceite: unitários que distinguem UTF-8 inválido/NUL de truncamento e cobrem os contextos acima, teste TCP com motivo `0x81`, fechamento, Will e ausência de mutação, regressões P190/P194 e MQTT 3.1.1. Gates WSL proporcionais: fmt, suíte completa, Clippy, build release, licenças e distribuição; CI do commit exato. Registrar falhas reais antes de correção. Marcar apenas P195; fase 6A global aberta e sem tag/release isolada.

Revisão 2: a primeira compilação do teste direcionado falhou antes de executar testes (`E0308`): `parse_subscription_user_property` passou a retornar erro boxed, mas dois retornos de limites locais ainda entregavam `&'static str` diretamente. Converter esses dois retornos com `.into()`, sem mudar a política de limites, e repetir os testes. A primeira tentativa é FAIL de compilação, não evidência funcional.
