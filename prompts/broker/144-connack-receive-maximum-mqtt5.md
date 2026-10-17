# P144 rev3 — Receive Maximum do broker no CONNACK MQTT 5

Entrada: broker 0.22.0/P143 aceito; client C80 em validação. Este prompt precede qualquer mudança funcional P144. A fase 6C permanece aberta.

Objetivo: anunciar no CONNACK MQTT 5 o limite de PUBLISH QoS1/2 simultâneos que o broker recebe, derivado de `limits.max_inflight` (1..32). Não confundir com o Receive Maximum enviado pelo client em CONNECT, que limita a direção broker→client. Preservar CONNACK MQTT 3.1.1, motivo de recusa, Session Present, Maximum Packet Size e Topic Alias Maximum existentes. Quando `Maximum Packet Size` anunciado pelo client impedir a propriedade adicional, preservar o fallback existente, registrar precisamente a omissão e recusar excesso de estado sem commit parcial. A propriedade não é durável nem vira quota por identidade.

Aceite: vetores independentes de CONNACK para limite padrão e configurado, fronteiras de tamanho 5/7/8/9/10/12/13/15/16, conectividade com client XMQR e Mosquitto 2.0.22, publicações QoS0/1/2, overflow da quota inbound QoS2 sem commit parcial, reconexão/restart, testes de regressão P134/P136/P138/P139, fmt/test/Clippy/build/licenças/CI. Checklist parcial apenas após CI. Nenhuma release isolada; sem ESP32 físico.

Fonte normativa: OASIS MQTT 5 §3.2.2.3.2 e §4.9, https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html.

Revisão rev2 após falha local: cinco testes `connect_contract_tests` usavam comparação integral com o CONNACK P138 de 13 bytes; a propriedade 0x21 correta amplia esse pacote para 16 bytes. Atualizar os vetores independentes e prefixos esperados, sem reduzir assertivas de Session Present/Maximum Packet Size/Topic Alias, então repetir a suíte completa. Nenhum defeito de runtime foi observado no teste TCP P144.

Revisão rev3 após Clippy: `expect` na conversão do limite para u16 introduziu um panic desnecessário no construtor público; limitar defensivamente a `u16::MAX`. Os vetores de teste repetidos serão uma constante única, preservando comparação integral e evitando o limite de comprimento do teste. Repetir fmt/test/Clippy antes de aceitar.
