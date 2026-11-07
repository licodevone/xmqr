# P268 v1.3 — versões MQTT por listener

Entrada: Broker 0.43.0, `85f2bf9` em
`codex/p265-p266-xmqr-operacao`. Os gates anteriores mantêm o estado dos
respectivos registros. A fase 9 continua aberta.

Objetivo: permitir que cada endpoint aceite MQTT 3.1.1, MQTT 5 ou ambos,
inspirado em `accept_protocol_versions` do Mosquitto. Exemplo: uma porta
para dispositivos legados e outra reservada para MQTT 5.

Escopo: `src/configuration.rs`, `src/main.rs`, `src/mqtt/mod.rs`,
testes de configuração e guia TOML. Políticas opcionais
`[[listener_protocols]]` com `bind` exato e `accept_protocol_versions = [4, 5]`.
Endpoints sem política aceitam 4 e 5. Rejeitar listas vazias, duplicadas,
níveis desconhecidos e binds sem listener no startup e em `--check-config`.
Aplicar a política antes de autenticar ou abrir sessão, inclusive em WS/WSS.

Aceite de protocolo: CONNECT válido de versão bloqueada recebe CONNACK
`0x01` em 3.1.1 ou `0x84` em 5 e a conexão encerra. O MQTT 5 respeita
Maximum Packet Size, inclusive quando a resposta não cabe. Preservar
diagnósticos de CONNECT inválido e níveis desconhecidos. Referências:
[Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html),
[MQTT 3.1.1 §3.1.2.2](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
e [MQTT 5 §3.2.2.2 e §3.1.2.11.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Compatibilidade: configuração v1, opção aditiva e mudança por reinício.
Não acrescenta MQTT 3.1, reload, política de ACL ou migração de estado.
Por padrão preserva o comportamento atual. Uma versão bloqueada não cria
sessão, não provoca takeover nem publica Will.

Validação: TOML válido e negativos em processo isolado, CONNECT TCP real
para as duas versões, CONNACK e fechamento, limite de pacote mínimo e
regressões. Fmt, testes e Clippy com Cargo.lock. Registrar gates bloqueados
e aplicar tag de versão apenas após aceite do commit exato.

Revisão 1.1: separar leitura e resolução das políticas para reduzir o
tamanho de `parse` e `run` apontado pelo Clippy. Associar a política ao
transporte ao criar o listener. A fixture Windows iniciou o broker, mas
o sandbox recusou conexões loopback com WinError 10013. Manter a fixture
de wire em Unix como as demais integrações de conexão e registrar
separadamente a validação local de configuração.

Revisão 1.2: atualizar o P259 e a referência de versões publicadas com
tags e commits conferidos do Broker, Client/Bridge, Admin e Managers.
Prompts novos indicam os commits de entrada e as versões independentes.
Distribuir P268 somente após validar o commit candidato, inclusive wire
em Unix, CI Ubuntu e pacotes com checksum. A tag v0.43.0 continua
identificando a fonte original, de forma imutável.

Revisão 1.3: simplificar a resolução de caminhos com `Path::join` para
atender ao limite de linhas do Clippy em `Configuration::parse`. A semântica
para caminhos absolutos e relativos permanece a do carregamento anterior.
