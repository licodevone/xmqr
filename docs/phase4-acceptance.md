# Aceite da fase 4 — concluído no escopo definido

P100/B11 e P101/B09 passaram gates Rust e integração externa Ubuntu26/WSL;
P97/B10, P98/B12 e C47/C48/C50/C05 também têm suas evidências nos registros.
O broker e o client da fase 4 passaram os gates para as prereleases experimentais
0.14.0/0.12.0, com limites descritos no [plano](evolution-plan.md).

O aceite **global** da fase 4 está concluído no escopo finito da matriz. A
ESP32 DevKit V1 na COM4, com dois backups originais de 4 MiB conferidos,
executou a campanha física P102: handshake inicial mTLS, rejeição de chave
inválida sem perder a geração anterior, certificado novo, rejeição de CA
desconhecida, recuperação da CA, revogação por CRL e recuperação da CRL.
Todos os 16 marcadores esperados apareceram em ordem, com seis sinais SIGUSR1,
firmware gravado e verificado e recursos Docker removidos. Veja o
[registro P102](../prompts/registros/P102-e02-fisico.md) e o
[resultado sanitizado](results/p102-e02-2026-10-15.json).

O ensaio não prova operação prolongada, falha de energia, revogação imediata
de sessões já estabelecidas, conformidade MQTT integral ou prontidão de produção.
