# Prompt — QoS 2 com estados duráveis

Execute após `25`, `26` e `27`. Referência: [OASIS MQTT 3.1.1, §§ 2.3.1, 3.3–3.7, 4.3.3, 4.4–4.6](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html). “Exactly once” é semântica do fluxo de entrega MQTT, **não** transação exatamente uma vez no sistema de negócio do assinante.

## Máquina de estados

1. Modele separadamente entrada e saída: PUBLISH→PUBREC→PUBREL→PUBCOMP. O identificador só é reutilizável após a conclusão do respectivo fluxo. Valide flags fixas (inclusive PUBREL=0x62), identificador não zero, comprimento, respostas inesperadas e duplicatas.
2. Na entrada, persista estado suficiente **antes de PUBREC** para evitar duas aplicações do mesmo PUBLISH após reinício. Defina ponto único e idempotente de encaminhamento ao roteador, inclusive se PUBREL se repetir. Persista avanço/liberação antes de PUBCOMP quando necessário para evitar perda ou repetição após crash.
3. Na saída, mantenha mensagem/estado até PUBCOMP. Reenvie PUBLISH não confirmado ou PUBREL pendente na retomada `CleanSession=0`, com mesmo packet identifier e regras de DUP aplicáveis; não converta QoS 2 silenciosamente em QoS 0/1. Ao transmitir, use `min(QoS da publicação, QoS concedido)` e respeite ACL e quotas.
4. Conexão antiga com o mesmo `client_id` não pode avançar o fluxo da geração nova. Limite inflight, retries, memória e fila de disco; não bloqueie o runtime por I/O. Em falha de persistência, feche/falhe fechado sem enviar confirmação que implique progresso durável inexistente.

## Prova

Escreva tabela de transição (estado, pacote, mutação, `fsync`, resposta) antes do código. Cubra perdas e duplicatas de cada pacote, crash antes/depois de cada commit e ACK, restart com sessão persistente, troca de conexão, IDs esgotados, fluxo inválido e carga concorrente. Faça teste externo com QoS 2 entre cliente Mosquitto e outro cliente independente em ambas as direções. Registre cláusulas e lacunas; não declare exatamente uma vez além da entrega protocolar observada.
