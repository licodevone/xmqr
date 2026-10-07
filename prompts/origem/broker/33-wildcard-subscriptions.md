# Prompt — filtros de assinatura `+` e `#`

Implemente filtros wildcard MQTT 3.1.1 depois do gate de Last Will ou em uma branch independente com contrato estável. Use OASIS MQTT 3.1.1 §§ 4.7 e regras de tópicos `$` como fonte normativa.

## Trabalho pedido

1. Separe `TopicName` de `TopicFilter` em tipos que não aceitem estados inválidos.
2. Valide `+` somente como nível inteiro e `#` somente como nível final inteiro; preserve níveis vazios e UTF-8 permitido.
3. Garanta que filtros iniciados por wildcard não casem implicitamente tópicos iniciados por `$`.
4. Projete índice/matcher limitado, sem busca exponencial, alocação ilimitada ou normalização de texto.
5. Aplique ACL ao filtro solicitado e também a cada entrega. Defina política segura quando a ACL atual só representa tópicos exatos.
6. Trate múltiplas assinaturas sobrepostas do mesmo cliente conforme QoS concedido e sem entrega duplicada indevida.
7. Integre retained, sessão persistente, UNSUBSCRIBE e restore após restart.

## Testes obrigatórios

Vetores normativos, níveis vazios, `sport/+`, `sport/#`, raiz, `$SYS`, filtros inválidos, Unicode, filtros profundos, muitas assinaturas, ACL, retained, reconexão e interoperabilidade com Mosquitto.

## Gate

Inclua property tests do matcher, benchmark de pior caso e limites configuráveis. Não habilite wildcard em produção antes de passar por segurança, carga e interoperabilidade.
