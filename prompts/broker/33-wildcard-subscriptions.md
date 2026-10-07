> **Adaptação XMQR — 2026-10-07.** Implementação existente: filtros +/# estão presentes na série 0.5 em desenvolvimento. Usar para auditoria/regressão; Last Will não é pré-requisito do comportamento já implementado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/33-wildcard-subscriptions.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — filtros de assinatura `+` e `#`

Audite os filtros wildcard MQTT 3.1.1 já presentes na série 0.5. Não reaplique a implementação nem dependa de Last Will. Corrija somente divergências incluídas em pedido específico. Use OASIS MQTT 3.1.1 §§ 4.7 e regras de tópicos `$` como fonte normativa.

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
