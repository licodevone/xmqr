# P138 rev7 — Topic Alias de entrada MQTT 5

Entrada: `main` após P137, broker 0.20.0 publicado, fases 6A–6D abertas. Criar este prompt antes de alterar o codec e o estado da conexão.

Objetivo: aceitar Topic Alias no PUBLISH recebido por uma conexão MQTT 5, com tabela limitada e exclusiva daquela conexão. Anunciar Topic Alias Maximum no CONNACK de sucesso apenas quando o pacote completo couber no Maximum Packet Size do cliente. Um PUBLISH com nome não vazio e alias válido substitui a associação; um PUBLISH seguinte com nome vazio resolve a associação. Alias zero, acima do máximo, não estabelecido, duplicado no mesmo pacote, nome vazio sem alias e propriedades truncadas encerram a conexão sem publicar. MQTT 3.1.1, ACL, QoS, retained, expiração e estado durável seguem a usar o tópico expandido. Reconnect e takeover começam com tabela vazia; nenhum alias é salvo em sessão persistente. Não anunciar alias de saída nem conformidade MQTT 5 integral.

Aceite: testes unitários do codec e da tabela (incluindo troca, limites, negativos e reinício de conexão); integração TCP real para QoS0/1/2 e ACL com client independente/Mosquitto onde suportado; regressão MQTT 3.1.1, P134/P136, fmt, testes, Clippy, build e CI. Documentar limite e evidência, atualizar checklist como entrega parcial e fazer commit/push depois do aceite. Sem teste físico ESP32 nesta etapa.

Revisão após o primeiro gate: cinco testes legados de CONNECT falharam porque fixavam exatamente 10 bytes para CONNACK; o novo anúncio válido tem 13 bytes. Atualizar os vetores para consumir o pacote completo anunciado e repetir os testes. Manter verificação de CONNACK reduzido quando Maximum Packet Size do cliente é 5–12 bytes.

Revisão após o segundo gate: todos os testes passaram (159 + integrações Rust; 6 ignorados), mas Clippy `-D warnings` reprovou a conversão direta do máximo de alias `u16` para `u8` no vetor CONNACK. Representar o limite local como `u8`, ampliar explicitamente para `u16` na comparação e repetir Clippy/build e integrações afetadas.

Revisão após o terceiro gate: a suíte principal passou novamente, porém o teste adicional de ACL escrito durante o gate não compilou em Clippy por tomar fatias de arrays temporários no `assert_eq!` (E0716). Construir o vetor esperado em variável com vida suficiente; executar novamente teste ACL, Clippy e integrações. Não tratar o teste anterior como aprovação deste acréscimo.

Revisão após o quarto gate: teste ACL PASS, mas Clippy detectou que a função de contrato cresceu além do limite de linhas (127/100). Extrair o envio/verificação do PUBLISH com alias para helper local e repetir Clippy/teste antes de validar as integrações.

Revisão após o quinto gate: o helper reduziu a função, mas ela ainda mede 104/100 linhas e Clippy falha. Extrair também a sequência de quatro tentativas de ACL para helper próprio; repetir os gates.

Revisão após o sexto gate: ACL/Clippy/build e percurso raw/client do script passaram, mas a etapa Mosquitto falhou porque `mosquitto_pub` usou Client Identifier vazio, recusado pela política XMQR existente. Fornecer `-i alias-external` ao fixture externo e repetir as integrações; não alterar a política de Client ID por este teste.
