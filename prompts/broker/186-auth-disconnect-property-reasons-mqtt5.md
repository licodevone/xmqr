# P186 — propriedades de AUTH/DISCONNECT MQTT 5 com motivo contextual

Entrada: P181/P183–P185 classificam erros de propriedades em assinatura, CONNECT/Will e PUBLISH. AUTH e DISCONNECT do client ainda fecham silenciosamente quando o identificador é fora de contexto ou quando uma propriedade única se repete. Este prompt precede o código P186.

Objetivo: após CONNACK MQTT 5, AUTH e DISCONNECT com identificador de propriedade fora do contexto recebem DISCONNECT `0x81`; duplicata de Authentication Method/Data/Reason String em AUTH e de Session Expiry/Reason String em DISCONNECT recebem `0x82`. User Property continua repetível. Preservar a exigência atual de método/dados e reason code `0x19` no AUTH, os motivos permitidos do DISCONNECT do client, a transição de Will por erro, o limite de pacote de saída, MQTT 3.1.1 e a persistência sem aplicação parcial de Session Expiry. Não classificar truncamento, UTF-8 inválido, valores de razão inválidos, quotas ou limites locais nesta fatia.

Aceite: unitários por identificador/duplicata, TCP de AUTH e DISCONNECT com Will e estado durável inalterado, negativos malformados e 3.1.1, regressões P131/P159/P172/P174/P181/P183–P185, fmt/test/Clippy/build/licenças/distribuição e CI. Atualizar registro, matriz e checklist como recorte parcial 6A/6B/6D, sem migração nem tag isolada.
