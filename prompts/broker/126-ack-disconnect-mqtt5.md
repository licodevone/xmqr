# P126 rev1 — formas normativas de ACK e DISCONNECT MQTT 5

Entrada: `main` após prerelease broker 0.17.0, fase 6A ainda aberta. O codec aceita ACKs MQTT 5 apenas na forma abreviada de dois bytes e DISCONNECT normal apenas com zero ou um byte, embora a OASIS MQTT 5 permita Reason Code de sucesso explícito e Property Length zero. Fonte: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), seções 3.4–3.7 e 3.14.

Objetivo: aceitar em PUBACK/PUBREC/PUBREL/PUBCOMP MQTT 5 as formas de sucesso abreviada, Reason Code `0x00` explícito e comprimento de propriedades zero explícito; aceitar o mesmo para DISCONNECT normal. Não alterar o comportamento MQTT 3.1.1 ou os transições duráveis existentes.

Limites: motivos de falha nos ACKs, propriedades não vazias e DISCONNECT com Will/expiração continuam fora do subconjunto e devem falhar fechados. Validar IDs não zero, truncamento, comprimento e bytes excedentes. Testes de codec positivos/negativos para cada ACK e DISCONNECT, suíte completa, fmt, Clippy, build, inventário MIT, integração externa e CI do commit. Documentar o subconjunto sem declarar 6A concluída. Sem bump/tag automática nesta fatia após a release 0.17.0.
