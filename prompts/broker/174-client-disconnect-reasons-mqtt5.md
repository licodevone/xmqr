# P174 rev1 — motivos de erro DISCONNECT enviados pelo client MQTT 5

Entrada: P172 aceita `0x00` e `0x04`. A [tabela 3-10 do MQTT 5 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) também permite que o client envie `0x80`, `0x81`, `0x82`, `0x83`, `0x90`, `0x93`, `0x94`, `0x95`, `0x96`, `0x97`, `0x98` e `0x99`; os demais códigos da tabela são exclusivos do servidor. Este prompt precede o código.

Objetivo: reconhecer apenas esses motivos do client, com os mesmos campos validados de P172. Só `0x00` cancela o Will; os outros motivos usam a transição durável de encerramento com Will. Registrar o código, nunca Reason String/User Property arbitrárias. Rejeitar motivo não definido ou exclusivo do servidor e preservar o MQTT 3.1.1. Sem migração de estado.

Aceite: vetor de todos os códigos permitidos e de recusas por direção, TCP real com motivo de erro, Will atrasado/restart, Session Expiry e conexão fechada; regressões P172, Rust/fmt/Clippy/build release/licença/distribuição e CI. Atualizar a matriz/checklist parcial; sem tag/release isolada e sem alegar aceites globais.
