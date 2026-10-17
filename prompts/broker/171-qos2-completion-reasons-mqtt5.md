# P171 rev2 — motivos e diagnósticos de PUBREL/PUBCOMP MQTT 5

Entrada: P170 conclui PUBREC negativo, mas o codec ainda aceita apenas sucesso sem propriedades em PUBREL e PUBCOMP. A [norma OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), seções 3.6, 3.7 e 4.3.3, admite `0x00` e `0x92` nesses pacotes e exige resposta PUBCOMP ao PUBREL. Este prompt precede o código.

Objetivo: analisar os dois motivos válidos, inclusive forma abreviada de sucesso, Reason String única e User Property repetida. Recusar ID zero, motivo/propriedade inválidos, duplicata, truncamento e extensões em MQTT 3.1.1. Ao receber PUBREL, manter a transição QoS2 e emitir PUBCOMP; ao receber PUBCOMP `0x92`, encerrar a tentativa de saída, liberar ID/quota e manter a conexão. Registrar apenas o código de motivo, sem conteúdo diagnóstico arbitrário. Não alterar o documento de estado.

Aceite: vetores positivos/negativos de codec, TCP real cobrindo ambos os motivos, entrega seguinte na mesma conexão e restart sem replay. Executar testes Rust, fmt, Clippy, build release, licença, distribuição e CI; registrar resultados e atualizar checklist sem declarar a fase 6A/6C concluída. Sem tag/release isolada.

Revisão 2: a primeira CI do código não iniciou os jobs por um recuo incorreto na nova etapa YAML. Antes da correção, acrescentar validação sintática do workflow e repetir a CI na fonte corrigida; não contabilizar a tentativa inválida como aceite.
