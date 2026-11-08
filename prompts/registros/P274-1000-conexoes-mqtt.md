# Registro P274 — quota de 1.000 conexões MQTT

Data local: 2026-11-07, America/Sao_Paulo.
[Prompt P274 v1.0](../broker/274-1000-conexoes-mqtt.md).
Base `389c4897aeaef143f60a4ff496d320e7e45c2913`.

- Faixas configuráveis de conexões e sessões de 1 a 1.000.
  Padrão 64, configuração 500 válida, estado v16 e orçamento
  agregado de 1.000.000 bytes preservados.
- PASS: fmt e diff-check. Biblioteca: 249 PASS, 1 ignorado,
  1 filtrado (monitor TCP). Configuração: 9 PASS, 1 ignorado
  no Windows. Versão: 2 PASS.
- PASS: 1.000 sessões vivas no ator com armazenamento real, recusa da
  1.001ª sessão, recusa ao reabrir com quota de 500 e recuperação de
  todas as sessões ao reabrir com 1.000.
- PASS: Clippy com `-D warnings -A unused_imports -A dead_code` para
  avisos preexistentes do alvo Windows. Scripts: 7 testes da fixture
  P80 e validação do seletor 500/1.000 do P272.
- BLOCKED: a fixture TCP explícita falhou na primeira conexão
  com WinError 10013. Em Ubuntu, executar:

  ```sh
  cargo test --locked --test configuration tcp_admits_1000_mqtt_clients_rejects_excess_and_reuses_slot -- --exact
  ```

- Pendentes o ensaio integrado, carga sustentada/mTLS e gates de
  pacote e publicação do candidato com P274.
