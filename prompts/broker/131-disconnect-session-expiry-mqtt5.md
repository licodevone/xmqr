# P131 rev1 — Session Expiry no DISCONNECT MQTT 5

Entrada: `main` após P130. O broker aceita Session Expiry no CONNECT, mas DISCONNECT MQTT 5 só aceita sucesso sem propriedades.

Objetivo: aceitar propriedade Session Expiry Interval (0x11) opcional no DISCONNECT normal e aplicar atomicamente a nova política ao encerrar a sessão. Permitir 0, finito ou infinito quando CONNECT iniciou sessão persistente; recusar transição de CONNECT expiry=0 para DISCONNECT expiry>0, duplicata, propriedade incorreta e frame truncado. Fonte: [OASIS MQTT 5 §§3.14.2.2.2 e 3.14.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: codec, roteador, persistência existente v7, testes wire e integração de retomada/expiração após reinício; sem nova opção do client independente enquanto a biblioteca rumqttc não expõe propriedades de DISCONNECT. Manter compatibilidade 3.1.1 e guardas de cancelamento. O comando do ator deve unir alteração e encerramento em uma transição durável.

Aceite: casos 0/finito/infinito, proibição de reviver sessão que iniciou com zero, negativos do codec, falha de armazenamento sem ACK de sucesso, regressão e CI verde. Registrar claramente o limite do client.
