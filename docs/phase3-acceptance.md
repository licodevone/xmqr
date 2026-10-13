# Fase 3 — registro de aceite dos três sistemas

Estado: **EM VALIDAÇÃO**, em 13 de outubro de 2026. Não equivale a release,
homologação de produção ou conformidade MQTT completa. Candidatos: broker e
admin legado 0.11.6, client 0.9.0. O admin independente mantém 0.1.0 e seu pin.

## Gates observados e pendentes

| Gate | Evidência observada | Situação do fechamento |
| --- | --- | --- |
| B06 — falhas de armazenamento | P86: 54 casos determinísticos; nova suíte nativa pré-P95 passou | Repetição no código final P95 requerida |
| B07 — fuzzing limitado | P90: 18 processos, três seeds, mutações reais, corpus e watchdog; PASS local | Repetição no código final P95 requerida; não é LibFuzzer/ASAN |
| B08 — wire e interoperabilidade | Wire candidato 19/19; C43 candidato 59/59; extensão descobriu encerramento TLS abrupto | Matriz completa após P95 pendente |
| B08 — campanha prolongada | Repetição inicial 600s TCP/mTLS passou, mas campanha completa falhou; tentativas posteriores preservadas | Três repetições integrais de pelo menos 600s ainda pendentes |
| C07 — robustez do client | C45/C46: 63 testes, idle90s real e cancelamento; clone exato e688c75 clean passou oito gates e gerou .deb | Extensão externa e ciclo do pacote ainda pendentes |
| Compatibilidade do admin 0.1.0 | Formato/pin não alterados por esta fatia | Integração dos 18 cenários contra o broker final requerida |
| Capacidade e peer não leitor | P94/P80: 60/60 no candidato anterior ao fix TLS | Repetição no ELF final requerida |
| Licenças e distribuição | Imagens candidatas e .deb client conferidos; originais de terceiros e MIT preservados | Pacote broker, ciclo Ubuntu26, imagens finais e publicação pendentes |

A falha TLS foi reproduzida independentemente: DISCONNECT normal produziu
EOF limpo; SIGTERM produziu ragged EOF em TLS1.2 e TLS1.3, inclusive com um
handshake parcial concorrente. P95 corrige a fronteira de fechamento e a
espera das conexões, com um único prazo total e preservação do erro de disco.
Essa correção precisa dos gates posteriores; uma hipótese ou teste unitário
isolado não substitui a campanha completa.

## Fontes e responsabilidades

Broker decide protocolo, autorização e persistência. Client comprova envio,
recebimento, cancelamento e recuperação. Admin independente é compatível no
recorte atual de CLI/offline e painel de leitura, sem criar canal administrativo
online nem segundo escritor do WAL.

Fonte exata candidata do client: e688c75a3779803e8f1868792dcc5e7a36f2dd6e.
Seu ELF nativo tem SHA-256 a7a89dba2245f56d4161d52a9767441257edca04be8042edcabf358e4bb05f58;
o clone e o build exatos estão no [registro C46](../../xmqr-client/prompts/registros/C46-release-fase3.md).
O checkpoint de código final do broker e os hashes de artefatos só serão
registrados depois de congelar e validar P95. Commits de documentação
posteriores não serão apresentados como fonte de pacotes que não reconstruíram.

Registros: [P90](../prompts/registros/P90-fuzzing.md),
[P91](../prompts/registros/P91-campanhas-robustez.md),
[P93](../prompts/registros/P93-contrato-connect.md),
[P94](../prompts/registros/P94-orcamento-nao-leitor.md),
[prompt P95](../prompts/broker/95-encerramento-tls.md) e
[planejamento integrado do admin](../../xmqr-admin/docs/planejamento-tres-sistemas.md).

## Limites

MQTT 3.1.1 é o protocolo desta fase. MQTT 5 continua planejado na fase 6,
sem implementação anunciada. Fases 4/5, rotação TLS, listeners adicionais e
administração online não são iniciados por este fechamento. Não há novo teste
físico ESP32 nesta fatia, nem homologação de Windows broker, arm64, MSRV1.88
exato, dias de estabilidade, throughput máximo ou perda física de energia.
O código próprio conserva MIT; as dependências mantêm suas licenças originais.
