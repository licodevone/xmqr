# P119 rev1 — razão de recusa ACL para PUBLISH MQTT 5 QoS 1

Data: 2026-10-16. Entrada: `main` `14f060b`, broker 0.16.0 experimental, P115/P116 aceitos; P118 classificou a falha de CI como intermitente após 30 repetições locais, suíte completa e rerun remoto PASS. Escopo da fase 6A.

## Objetivo e escopo

Quando uma publicação MQTT 5 QoS 1 é recusada pela ACL, responder PUBACK com reason code `0x87` (Not authorized), sem enviar a mensagem ao roteador nem alterar retained/estado; manter a conexão para operações autorizadas posteriores. O cliente MQTT 3.1.1 mantém o fechamento existente; MQTT 5 QoS 0 mantém o fechamento até uma entrega própria para DISCONNECT com motivo. Codificar PUBACK com reason code e propriedades vazias segundo OASIS MQTT 5 §3.4.2. Arquivos: `src/mqtt/{codec,mod,connect_contract_tests}.rs`, docs de conformidade, plano, changelog e registro P119.

## Limites e aceite

Preservar o PUBACK abreviado de sucesso, quotas, autenticação e deny-by-default. Testar bytes de resposta e ACL real em conexão MQTT 5: recusa `0x87`, ausência de commit, publicação permitida posterior na mesma conexão; regressão MQTT 3.1.1. Gates Rust, interop e CI. Sem alterar versão ou formato durável; tag/release somente em marco posterior aceito.

Fonte normativa: <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>, §3.4.2 e tabela 3-4.

Rev2: `cargo test --locked` passou, mas Clippy all-targets recusou o novo teste de integração por 103 linhas (limite 100). Extrair a construção repetida de CONNECT autenticado em helper de teste, sem suprimir lint, e repetir os gates.
