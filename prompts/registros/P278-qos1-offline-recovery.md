# P278 — recuperação de publicação QoS 1 offline

2026-11-08, America/Sao_Paulo. [Prompt](../broker/278-qos1-offline-recovery.md).

- PASS: validação de sintaxe Python. A campanha incluiu um caso que usa
  três processos sequenciais sobre estado temporário. O primeiro cai após
  confirmar a publicação, o segundo cai após uma barreira PINGRESP do ACK
  do assinante e o terceiro verifica ausência de nova entrega.
- BLOCKED: a campanha exige Linux/WSL. O guard retornou o pré-requisito
  no Windows. Nenhum resultado de recuperação do novo caso foi aprovado.
