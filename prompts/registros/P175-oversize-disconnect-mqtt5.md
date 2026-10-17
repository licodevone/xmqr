# P175 — pacote excessivo recebe DISCONNECT `0x95` parcialmente

O [prompt P175](../broker/175-oversize-disconnect-mqtt5.md) foi commitado antes da funcionalidade (`ab9a93f`). Fonte exata `ed067b14794dc0804a7fe867219a8065a74978f5`: 200 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39026234732) nos jobs Rust e pacote Ubuntu 26.04, incluindo testes Mosquitto/Paho e TCP P169–P175.

O erro de enquadramento por limite local de 64 KiB agora tem tipo próprio. Após CONNACK MQTT 5, o broker envia DISCONNECT `0x95` dentro do Maximum Packet Size negociado e fecha; não lê o corpo anunciado nem aplica estado parcial. Falhas de transporte, timeout e outros erros continuam separados. `scripts/verify_mqtt5_oversize_disconnect.py` retornou `P175_OVERSIZE_DISCONNECT_PASS`: bytes `e0 02 95 00`, fechamento, publicação do Will, e fechamento sem DISCONNECT MQTT 5 para cliente 3.1.1.

Sem migração nem tag/release isolada. Outros motivos de erro enviados pelo broker e aceites globais 6A/6C continuam abertos.
