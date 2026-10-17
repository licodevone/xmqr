# P175 rev1 — DISCONNECT `0x95` após pacote MQTT 5 grande demais

Entrada: P174 aceita motivos válidos enviados pelo client. Após CONNACK de sucesso, um quadro acima do limite global é fechado sem motivo MQTT 5. Pela [norma OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), 3.14.2/4.13, `0x95` indica Packet too large. Este prompt precede o código.

Objetivo: classificar apenas excesso do limite de quadro/buffer como erro de tamanho, emitir DISCONNECT `0x95` limitado pelo Maximum Packet Size negociado após CONNACK MQTT 5 e encerrar sem interpretar o corpo nem gravar estado parcial. Se a escrita falhar, preservar a limpeza de sessão/Will; MQTT 3.1.1 mantém fechamento sem DISCONNECT MQTT 5. Não converter timeout, EOF, TLS/I/O nem outros erros de protocolo em `0x95`. Não alterar o documento durável.

Aceite: teste TCP real com cabeçalho que excede o limite, bytes de DISCONNECT e fechamento, comparação MQTT 3.1.1, sessão/Will sem commit indevido; unitários de enquadramento, Rust/fmt/Clippy/build release/licenças/distribuição e CI. Atualizar matriz e checklist parcial. Sem tag isolada e sem alegar fase 6A completa.
