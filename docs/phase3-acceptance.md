# Fase 3 — aceite de robustez dos três sistemas

**ACCEPTED no recorte finito validado**, em 13 de outubro de 2026. Broker e
mqtt-admin legado 0.11.6, client 0.9.0; admin independente mantém 0.1.0,
pin e distribuição anteriores. Publicação nova em preparação neste checkpoint.
Não equivale a produção, SLA ou conformidade MQTT completa.

## Critérios cumpridos

| Gate | Resultado final observado |
| --- | --- |
| B06 — armazenamento | 54 casos determinísticos reexecutados na suíte final; sem tratar erro como EOF/ACK indevido |
| B07 — fuzzing limitado | 18/18 processos, três seeds, 300.000 mutações rápidas, restore/estado/roteador e watchdog; fontes estáveis |
| B08 — wire e TLS | 19/19 vetores; 12/12 encerramentos TLS1.2/1.3, handshake parcial e TLS completo sem CONNECT |
| B08 — matriz externa | 87/87:59 C43 +28 extensões; XMQR/Mosquitto2.0.22 nos dois sentidos, mTLS/ACL/reconexão/crash/idle |
| B08 — ensaio prolongado | 6/6, três repetições TCP/mTLS >=600s; 1808,946s de parede e mais de 60 processo-minutos |
| C07 — client | 63 testes, idle90s real, cancelamento/jitter/prazo total, clone clean e interop ampliada |
| Admin independente | 18/18 compatibilidade0.1.0 com broker final; sem repin ou novo canal administrativo |
| Capacidade/shutdown | 60/60 P80 no ELF final; três testes adicionais, inclusive snapshot falho com exit não-zero |
| Fonte/artefatos | Clones clean, fmt/test/clippy/build/inventário; oito gates por pacote, versões/hashes reais |
| Licenças/instalação | QA5/5 e14 negativos; ciclo Ubuntu26 install/upgrade/rollback/remove/purge e ELFs instalados executados |

Soak:40.512 publicações de1024bytes/162.048 entregas fan-out,90crashes/30SIGTERM.
Finais saudáveis com zero erros/filas/estado transitório. Todos1698probes
registrados, inclusive quatro ready0 transitórios; recuperação máxima1,659s,
dentro do prazo quiescente15s. Isso não é SLA de readiness ou throughput.
RSS máximo amostrado7392KiB TCP/48520KiB mTLS; arquivos duráveis890870bytes.
Crescimento por geração registrado; RSS/restart não prova ausência de leak.
Estado privado /var/tmp disk-backed, não /tmp tmpfs dos ensaios invalidados.

## Fonte exata e proveniência

Broker: abbe38ca6c041f7328e85054506a4eed22c74c41, ELF nativo SHA-256
e57b1e2d26de50d09bb6bdadb74e4c0531dcac15399ece4369f4e0a0824e2987.
Admin legado f40ecbb5e1641565bbf6ec2cb0e14a7d58973709270bc89c64070ae32b6f9083.
Client: e688c75a3779803e8f1868792dcc5e7a36f2dd6e, ELF nativo
a7a89dba2245f56d4161d52a9767441257edca04be8042edcabf358e4bb05f58.
Rebuilds clean coincidiram nesses bytes, sem promessa geral de reproducibilidade.
Imagens Bookworm têm ELFs próprios e testes Docker, não os ELFs Ubuntu renomeados.

O soak começou antes do commit final: JSON conserva HEAD3a5e29d/dirty=true.
As26entradas src/Cargo permaneceram invariantes e o ELF efetivamente copiado/
executado corresponde ao rebuild clean abbe. Não apresentar execução original
como checkout clean nem reescrever JSON. Interop usou IDs imutáveis/revisionsabbe/e688.

Terceiros comparados byte a byte: broker/admin113pacotes/218textos; client81/158.
MIT/copyright próprios preservados, comparação somente CRLF→LF. Superset do lock,
não SBOM completo do ELF/auditoria jurídica. Gitleaks do delta passou, não auditoria integral.

## Falhas preservadas e limites

P93 reproduziu recusas CONNECT incorretas; P95 reproduziu TLS EOF abrupto,
inclusive sem MQTT. Fixes RED→GREEN. Campanhas antigas parciais/FAIL, ENOSPC
observado e lançamentos WSL que não iniciaram permanecem registrados; não
foram promovidos nem foi alegada limpeza de cache por nós.

Duas matrizes intermediárias falharam em readiness ACL/subscriber externo;
as causas exatas dessas ocorrências não foram recuperadas. Telemetria específica
e prova SUBACK/recusa foram acrescentadas sem aceitar exit arbitrário. Will6,
contratos21 e matriz completa final passaram sem ampliar W8. Falhas permanecem
limitação histórica, não prova de causa ambiental/estabilidade ilimitada.

MQTT3.1.1 é o protocolo desta fase. MQTT5 segue planejado na fase6, não iniciado.
Fases4/5, rotação TLS, listeners adicionais e administração online não entregues
aqui. Sem novo ESP32 físico, Windowsbroker/arm64/MSRV1.88 exato homologados,
perda física de energia, estabilidade de dias ou throughput máximo.

## Registros e próximos marcos

[P90](../prompts/registros/P90-fuzzing.md), [P91](../prompts/registros/P91-campanhas-robustez.md),
[P92](../prompts/registros/P92-aceitacao-distribuicao-fase3.md),
[P93](../prompts/registros/P93-contrato-connect.md), [P94](../prompts/registros/P94-orcamento-nao-leitor.md),
[P95](../prompts/registros/P95-encerramento-tls.md) e
[C46](../../xmqr-client/prompts/registros/C46-release-fase3.md).
Reports finais sanitizados serão anexados à distribuição; intermediários são
evidência local e histórico explícito. As fases4/5 têm o
[planejamento integrado do admin](../../xmqr-admin/docs/planejamento-tres-sistemas.md).
Próximo código exige novo prompt, não iniciou por encerrar a fase3.
