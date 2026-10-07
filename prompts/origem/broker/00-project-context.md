# Contexto editável do projeto

> Edite este arquivo. Substitua `A DEFINIR` apenas quando houver uma decisão. Se algo permanecer indefinido, os agentes devem apresentar opções e registrar a decisão antes de implementar dependências irreversíveis.

## Produto

- Nome público do broker: `A DEFINIR`
- Objetivo atual: `broker MQTT 3.1.1 educacional e verificável, usado pelos laboratórios ESP-IDF do curso`
- Usuários principais nesta fase: `alunos, instrutores e desenvolvedores em laboratório controlado`
- Gateway MQTT/API ou posicionamento industrial/edge: `fora da fase atual; preservar somente como evolução futura`
- Compatibilidade de referência: Mosquitto no comportamento observável, sem copiar código
- Licença pretendida: `A DEFINIR`
- Plataformas comprovadas: `Linux x86_64 no WSL/Ubuntu; outras exigem gate próprio`
- Política de estabilidade da configuração/API: `A DEFINIR`

## Escopo MQTT

- Versão inicial: `MQTT 3.1.1`
- Versão seguinte: `MQTT 5.0`
- MQTT 3.1 legado: `fora do escopo, salvo decisão contrária`
- Transporte TCP: `sim`
- Endereço do broker: `descoberto/configurado por ambiente; nunca copiar IP de outra máquina`
- Porta MQTT segura padrão: `8883`; laboratório aberto local: `127.0.0.1:1883`
- TLS: `sim no modo padrão secure-mtls; não nos modos didáticos open-lab, password-lab e acl-lab, todos restritos a loopback`
- WebSockets: `A DEFINIR`
- Unix sockets: `A DEFINIR`
- Shared subscriptions: `fase MQTT 5.0`
- Subscription identifiers, aliases e flow control MQTT 5: `A DEFINIR`

## Sessões e persistência

- Sessões persistentes: `sim`
- Backend atual: `WAL append-only próprio e snapshots versionados; consultar docs/architecture/persistence.md`
- Garantia atual de durabilidade: `ACKs que transferem responsabilidade somente após commit/fsync definido; consultar ADR e limitações`
- Retained messages: `sim`
- Last Will: `planejado no prompt 32; ainda não implementado na versão 0.5.0`
- Limite de fila offline: `A DEFINIR`
- Política de expiração/evicção: `A DEFINIR`
- Compatibilidade de formato entre versões: `A DEFINIR`

## Segurança

- Autenticação atual: `secure-mtls com certificado + usuário/senha; password-lab e acl-lab com usuário/senha sem certificado; open-lab anônimo`
- Autorização/ACL atual: `deny-by-default; PUBLISH por tópico concreto e SUBSCRIBE por filtro exato concedido, inclusive +/#, em secure-mtls e acl-lab; ausente em open-lab e password-lab`
- TLS mínimo: `TLS 1.2; preferir TLS 1.3 quando suportado pelo dispositivo`
- SAN obrigatório no certificado do servidor: `nomes/IPs reais usados no ambiente, descobertos antes da emissão`
- Listener anônimo: `somente MQTT_MODE=open-lab; todos os modos sem TLS têm bind tecnicamente limitado a loopback`
- Multi-tenancy: `A DEFINIR`
- Interface administrativa: `local/isolada; protocolo A DEFINIR`

## Escala e desempenho

- Conexões simultâneas alvo: `A DEFINIR`
- Throughput alvo: `A DEFINIR mensagens/s, com payload e QoS definidos`
- Latência alvo: `A DEFINIR p95/p99`
- Tamanho máximo de pacote: `A DEFINIR, limitado pelo protocolo e configuração`
- Tamanho típico de payload: `A DEFINIR`
- Fan-out típico e máximo: `A DEFINIR`
- Orçamento de memória por conexão: `A DEFINIR`
- HA/cluster: `fora do MVP; confirmar`

## Operação

- Formato de configuração: `TOML proposto; confirmar`
- Reload sem restart: `somente campos explicitamente seguros`
- Logs: `estruturados`
- Métricas: `Prometheus proposto; confirmar`
- Tracing: `OpenTelemetry proposto; confirmar`
- Container/systemd: `A DEFINIR`
- Política de upgrade e rollback: `A DEFINIR`

## Engenharia

- Rust edition/MSRV: `edition 2024, rust-version conforme Cargo.toml`
- Runtime assíncrono: `Tokio, conforme código e documentação atual`
- Política de dependências: `mínimas, mantidas e auditáveis`
- CI alvo: `A DEFINIR`
- Clientes de interoperabilidade obrigatórios: `mosquitto_pub/sub e pelo menos duas bibliotecas independentes`
- Regras adicionais do usuário: `não criar gateway na fase atual; preservar prompts futuros sem executá-los`
