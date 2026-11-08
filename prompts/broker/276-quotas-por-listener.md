# P276 v1.0 — quota de conexões por listener

## Entrada e objetivo

Base local `d128e47c04fa450b260d736555df69ea8c8aec71`, candidato
0.45.0 com quota global de até 1.000 conexões. Primeira fatia da
prioridade 10, para limitar a ocupação de um listener por planta.

## Escopo

Adicionar `[[listener_limits]]` com `bind` e `max_connections` em
`src/configuration.rs`, ligar a configuração ao startup e preflight em
`src/main.rs`, aplicar admissão em `src/transport/mod.rs` e registrar
recusas com motivo fixo em `src/monitoring.rs`. Atualizar documentação
e testes de configuração e admissão.

## Compatibilidade e requisitos

A quota local é opt-in e deve ser positiva, menor ou igual à global e
referir-se a um bind MQTT efetivo, sem duplicatas. A configuração
existente conserva o comportamento e as APIs públicas de transporte.
TCP, WS e WSS contam handshakes. Aquisição e liberação das duas vagas
ocorrem no ciclo da tarefa, com recusa antes de TLS/MQTT. A quota global
e a barreira de shutdown continuam compartilhadas. Preservar QoS, ACL,
TLS, protocolo MQTT e formato persistente. Os limites são tetos, com
uso do pool global pelas portas sem quota explícita.

## Aceite

Testar configuração, independência entre listeners, recusa local e
global, liberação de vaga em ambos os caminhos e métricas sem dados
sensíveis. Exercitar um TCP saturado e WS com vaga no mesmo processo.
Registrar evidências em `prompts/registros/P276-quotas-por-listener.md`.
Tag/release exige CI Ubuntu da fonte exata e pacote verificado.
