# ADR 0001 — Base de persistência com WAL e snapshot

Status: aceita para a camada inicial; não implica compatibilidade MQTT completa.

## Contexto

O broker precisa recuperar estado após queda sem bloquear as tasks de rede nem reproduzir a fragilidade de um único arquivo de estado regravado no lugar. O protocolo MQTT ainda não está implementado; esta decisão define apenas a fronteira de armazenamento.

## Decisão

Usar um escritor exclusivo em thread dedicada, acionado por fila Tokio limitada. Cada mutação individual é um registro WAL com sequência e CRC32, sincronizado por `sync_data` antes da confirmação. Snapshots contêm versão de formato, sequência e CRC32; são publicados por arquivo temporário, `sync_all`, rename e `fsync` do diretório antes da compactação do WAL. Recuperação rejeita corrupção completa e versões desconhecidas, mas descarta cauda incompleta.

`fsync` por registro é fixo nesta primeira versão. Não há transação multichave, rotação automática do WAL ou garantia de integridade criptográfica. Para mudanças futuras no formato, incrementar a versão, criar leitor/migrador explícito e testar upgrade/rollback em cópias de dados; não reinterpretar silenciosamente bytes antigos. Uma migração deve preservar os arquivos originais até validação completa e publicação atômica do novo estado.

## Consequências

A política privilegia durabilidade e simplicidade de recuperação, ao custo de throughput de escrita e possível crescimento do WAL até um snapshot ser solicitado. O serviço deve monitorar latência de sync e espaço livre. ACKs MQTT duráveis exigirão integração explícita com esta resposta de commit e testes de QoS; a mera existência do módulo não os implementa.

Alternativas deixadas para avaliação posterior: banco embutido maduro, agrupamento de commits com prazo máximo, WAL segmentado e snapshots incrementais. A adoção de qualquer uma exige benchmark, análise de falhas e plano de migração.
