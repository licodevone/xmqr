# Registro P271 — quota de 500 conexões MQTT

Data local: 2026-11-07, America/Sao_Paulo.
[Prompt P271 v1.3](../broker/271-500-conexoes-mqtt.md).
Base: `02097af27efe601ada936dc964d82936e6771e5a`.

- A configuração opt-in amplia conexões e sessões a 500, com padrão 64.
  Documento v16, orçamento de 1.000.000 bytes e demais quotas preservados.
- PASS: rustfmt e diff-check. A biblioteca teve 249 PASS, 1 ignorado
  e 1 filtrado (monitor dependente de TCP). Configuração: 9 PASS e 1
  ignorado na execução padrão Windows. Versão: 2 PASS.
- PASS: 500 sessões MQTT vivas registradas no ator com armazenamento
  real. Sessão excedente recusada. Abertura com quota de 64 falhou e a
  abertura seguinte com 500 recuperou o estado inteiro.
- PASS: Clippy com `-D warnings -A unused_imports -A dead_code`
  para excluir avisos conhecidos do alvo Windows. O lint de teste
  e o tamanho da fixture foram tratados nas revisões do prompt.
- BLOCKED: a execução explícita da fixture TCP falhou na primeira
  conexão com WinError 10013. O caminho de 500 clientes, recusa e
  liberação de vaga permanece disponível na integração Unix:

  ```sh
  cargo test --locked --test configuration tcp_admits_500_mqtt_clients_rejects_excess_and_reuses_slot -- --exact
  ```

- Carga sustentada, rajadas mTLS, pacote e tag/release aguardam validação.
