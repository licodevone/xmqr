# Aceite da fase 4 — em andamento

P100/B11 e P101/B09 passaram gates Rust e integração externa Ubuntu26/WSL;
P97/B10, P98/B12 e C47/C48/C50/C05 também têm suas evidências nos registros.
O broker e o client da fase 4 estão prontos para as prereleases experimentais
0.14.0/0.12.0, com limites descritos no [plano](evolution-plan.md).

O aceite **global** da fase 4 permanece aberto por E02. A ESP32 na COM4 foi
identificada, tinha backups válidos, recebeu firmware E02 verificado e iniciou,
mas falhou na associação Wi-Fi antes de qualquer rotação TLS física. O SSID
privado anterior não estava visível na varredura atual. Veja o
[registro P102](../prompts/registros/P102-e02-fisico.md). Só marcar E02 e a
fase 4 como concluídos após certificado, CA, CRL, recusas e recuperação serem
observados na placa e documentados. Não inferir produção ou conformidade ampla.
