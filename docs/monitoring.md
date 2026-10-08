# Monitoramento opcional - P43

Implementação local 0.7.0 validada em Unix, aguardando publicação pelo mantenedor. Desabilitado
por padrão, sem novas dependências. Configure antes de iniciar o broker:

```bash
export MQTT_MONITOR_ENABLED=true
export MQTT_MONITOR_BIND=127.0.0.1:9090
curl --fail http://127.0.0.1:9090/health
curl --fail http://127.0.0.1:9090/ready
curl --fail http://127.0.0.1:9090/metrics
```

`MQTT_MONITOR_ENABLED` aceita somente `true` ou `false`. O bind padrão é
`127.0.0.1:9090`; aceita IPv4/IPv6 loopback e porta não zero. Variáveis inválidas
falham na inicialização, mesmo com monitor desabilitado; porta ocupada quando
habilitado também falha explicitamente. Não há fallback para outra interface.
O monitor não oferece autenticação: qualquer processo com acesso ao loopback
pode consultar os agregados. Não exponha esse listener por proxy sem controle
de acesso próprio.

## HTTP e disponibilidade

Somente GET, HTTP/1.0 ou 1.1, uma requisição por conexão e sem corpo:

| Caminho | Resultado |
| --- | --- |
| `/health` | 200 enquanto o servidor HTTP atende |
| `/ready` | 200 com listener MQTT pronto e probe real do ator/writer; 503 caso contrário |
| `/metrics` | 200, texto Prometheus 0.0.4; inclui `xmqr_ready` atualizado pelo probe |

Probe possui timeout de 500 ms e envio não bloqueante à fila limitada do ator.
Consulta o writer sem copiar ou escrever estado. Readiness não mede espaço livre,
energia, rede do consumidor ou sucesso de negócio. Sob saturação/timeout pode
retornar 503 mesmo com processo vivo. Falha durável detectada mantém o caminho
MQTT fail-closed. `/health` pode continuar 200 quando o ator já parou.

HTTP admite 16 handlers simultâneos, cabeçalho até 4096 bytes, leitura e escrita
com timeout de 1 s. Rejeita excesso, corpo e Transfer-Encoding; códigos previstos:
400, 404, 405, 408 e 431. Excesso de conexões pode ser fechado sem resposta.
Respostas encerram a conexão e usam `Cache-Control: no-store`. O trabalho HTTP
possui limite próprio, mas os probes consomem capacidade do ator MQTT.
Destruir o monitor cancela listener/requests; não implementa shutdown gracioso
novo do broker. Falha de accept HTTP após startup encerra o monitor sem encerrar
o MQTT. Não há reinício automático do monitor.

## Semântica das métricas

Contadores são locais ao processo e zeram no reinício. Gauges agregam estado
observado; leituras atômicas relaxadas não formam snapshot transacional.

| Série | Semântica |
| --- | --- |
| `xmqr_connections_active/total` | handlers MQTT iniciados após transporte; active decresce por RAII |
| `xmqr_tcp_accepted_total` | sockets TCP aceitos, inclusive recusados por admissão |
| `xmqr_messages_received_total{qos}` | PUBLISH de cliente aceito após commit; QoS2 conta uma vez por ownership, não por retransmissão/PUBREL |
| `xmqr_messages_sent_total{qos}` | escritas de frames PUBLISH concluídas, inclusive retained, replay e Will |
| `xmqr_rejections_total{reason}` | eventos de authentication, authorization, quota, admission, delivery, persistence ou transport |
| `xmqr_persistence_commits_total` | commits concluídos; falha não conta como sucesso |
| `xmqr_persistence_commit_attempts_total` | tentativas de commit, inclusive rejeições de candidato |
| `xmqr_persistence_commit_duration_seconds` | summary sum/count de tentativas; validação/serialização e espera pelo writer, sem quantis |
| `xmqr_persistence_errors_total` | erros do writer/armazenamento; candidato inválido não implica erro de disco |
| `xmqr_persistence_snapshots_total` | snapshots concluídos |
| `xmqr_wills_published_total` | Will efetivamente publicado após transição durável, inclusive recuperação |
| `xmqr_offline_messages`, `xmqr_inflight_messages` | filas persistentes agregadas |
| `xmqr_delivery_messages_queued`, `xmqr_router_commands_queued` | filas observadas de entrega e comandos |
| `xmqr_sessions`, `xmqr_retained_messages` | estado persistente agregado |
| `xmqr_ready` | último resultado do probe, inicialmente zero |
| `xmqr_monitor_rejected_total` | rejeições HTTP contabilizadas pelo monitor |

Os únicos labels são QoS 0/1/2 e os sete motivos fixos. Não há payload, tópico,
username, Client ID, senha ou chave em labels. ACK MQTT e escrita do socket não
comprovam processamento pelo consumidor. Will interno não incrementa received.
Erros/rejeições representam eventos e não necessariamente mensagens únicas.
O commit de recuperação inicial pode contribuir aos contadores de commit.

## Compatibilidade e validação

Documento MQTT v2 (leitura v1), WAL/snapshot v1, quotas MQTT e MIT preservados.
Veja [registro P43](../prompts/registros/P43-0.7.0.md) para gates reais e bloqueios.
Windows compila, porém testes que abrem armazenamento exigem fsync Unix.
O aceite completo requer WSL/Linux na mesma cópia `/mnt/d/projects/my-project/xmqr`.
Não declarar release pronta com integração ou gates Unix pendentes.

## Gates reproduzíveis e evidência portátil

Antes de serving Unix, pode validar recusa de configuração no Windows/Linux:

```text
python -X utf8 scripts/verify_monitoring_startup.py --broker CAMINHO_DO_BROKER
```

Seis casos PASS no Windows: booleano inválido, porta zero, endereço remoto ou
genérico IPv4/IPv6 e bind inválido mesmo desabilitado. Todos recusam antes de
criar diretório de estado. Isso não aprova /health, /ready ou tráfego MQTT.

Em Linux/WSL, após gates Rust completos, use binários separados construídos:

```text
python3 scripts/verify_monitoring.py --broker CAMINHO_DO_BROKER --client CAMINHO_DO_CLIENTE
python3 scripts/verify_last_will.py --broker CAMINHO_DO_BROKER --client CAMINHO_DO_CLIENTE
```

O primeiro possui seis cenários HTTP/MQTT/contadores/filas/Will; o segundo
regressões independentes de Will/retained/1024 UTF-8. Não requerem Mosquitto.
Use binário Linux do cliente independente, não o .exe Windows dentro do WSL.
Esses cenários passaram em WSL na retomada final; os timeouts anteriores foram resolvidos.

## Resultado atual P43

2026-10-08:72 testes Unix, fmt/Clippy/inventário/build e6 integrações monitoring
mais9 regressões Will PASS, com cliente independente baseline26c1019. Seis
recusas de configuração reais também PASS. Histórico de bloqueios anteriores
não descreve o estado atual. Mosquitto/TLS/mTLS externo NOT_RUN. Aguardar
publicação do mantenedor; ver registro P43. Nenhuma implementação0.8 executada.
