# P176 rev1 — DISCONNECT `0x94` para Topic Alias inválido MQTT 5

Entrada: P175 envia motivo `0x95` para pacote excessivo. P138 já rejeita Topic Alias zero, maior que o anunciado ou não estabelecido, mas apenas fecha a conexão. A [norma OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), seção 3.14.2, define `0x94` para Topic Alias invalid. Este prompt precede o código.

Objetivo: classificar esses três erros de alias sem confundi-los com EOF/timeout/I/O, enviar DISCONNECT `0x94` após CONNACK MQTT 5 respeitando Maximum Packet Size e fechar antes de qualquer publicação/commit. A tabela de alias continua local à conexão. MQTT 3.1.1 e casos de alias válidos permanecem iguais; nenhum documento durável muda.

Aceite: vetores de zero, excedente e não estabelecido; TCP real com bytes `e0 02 94 00`, ausência de entrega, reset de conexão e regressão de alias válido/MQTT 3.1.1; Rust/fmt/Clippy/build release/licença/distribuição/CI. Atualizar o teste P138 e checklist parcial. Sem tag isolada nem aceite global 6C.
