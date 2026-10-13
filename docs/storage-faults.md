# Fase 3/B06 — falhas de armazenamento, P86

Aceite do recorte determinístico em2026-10-13, Ubuntu26/WSL, Rust1.99.
Broker/admin0.11.5; client0.8.1 mantido. A fase3 inteira continua aberta.

## Correção demonstrada

Na recuperação do WAL, uma leitura curta dos quatro bytes do tamanho era
completada com `read_exact(...).is_err()`. Isso confundia EIO com EOF e podia
truncar o arquivo a partir daquele registro. A leitura foi extraída preservando
esse comportamento; um Reader que fornece dois bytes e depois erro5 reproduziu
o defeito (RED). Após a correção, EIO é propagado (GREEN). Só UnexpectedEof
autoriza descartar cauda incompleta. Erro real de leitura não autoriza reparo
destrutivo nem abertura silenciosa. O Reader é controlado, não um disco avariado.

## Campanha aceita

Doze testes Rust novos cobrem54 casos/subcasos; integram a suíte123 testes.
As contagens abaixo descrevem as iterações efetivamente verificadas pelos testes,
não54 processos externos independentes nem54 falhas físicas de dispositivo.

| Recorte | Casos | Observação exigida |
| --- | ---: | --- |
| Leitura curta seguida de EIO | 1 | Propagar erro5, não transformar em EOF |
| EOF vazio/parcial e tamanho completo | 5 | Vazio normal; prefixos1/2/3 incompletos; tamanho completo |
| Append ENOSPC/EIO/prefixos/write-zero | 5 | Memória/seq anteriores, poison, reopen e retry novo |
| Escrita curta1/3bytes e Interrupted | 3 | write_all completa; sucesso só após sync |
| sync_data em put/delete | 2 | Sem sucesso nem mudança em memória; registro completo pode reaparecer |
| Snapshot/compactação:8fronteiras x EIO/ENOSPC | 16 | Estado já confirmado preservado na reabertura |
| Snapshot parcial | 1 | Temporário nunca promovido; descartado no reopen |
| WAL completo inválido | 7 | CRC/versão/tamanho/seq/duplicata/operação/valor recusados, arquivo idêntico |
| Writer assíncrono após falha | 1 | get/probe/put/delete/snapshot recusados; shutdown libera lock |
| Router: sessões online/offline | 1 | Candidato não exposto; todas as conexões vivas fechadas |
| Router: snapshot depois de commit durável | 3 | Resposta falha, sem fan-out; commit recuperável com outbound pendente |
| TCP:3fronteirasQoS x3falhas | 9 | Nenhum PUBACK/PUBREC/PUBCOMP nem fan-out indevido; EOF e reopen |

Fronteiras snapshot: create, write, sync do temporário, rename, sync do
diretório, truncate do WAL, write do header, sync da compactação. ENOSPC28
e EIO5 são injetados. Os diretórios são temporários no filesystem Linux local;
não se preenche disco. Hooks e comandos de injeção existem apenas emcfg(test),
por Store, sem variável de ambiente pública ou estado global entre testes.

Os nove casos TCP enviam bytes MQTT independentes do encoder do broker e passam
pelo transporte loopback, handler, ator, documento MQTT e writer reais. Um
observador já inscrito verifica que não há entrega após falha. A reabertura
verifica retained e responsabilidade inboundQoS2, não só a ausência de ACK.
O teste de snapshot no ator força o contador127 para atingir a fronteira128;
isso não é um ensaio prolongado de128publicações nem um novo teste TLS.

## Resultado incerto não significa ausência de gravação

Em erro de append parcial, só o registro incompleto é descartado. Em erro de
fsync, o WAL pode conter o registro inteiro: nesta injeção ele reaparece após
reopen, sem ACK anterior. No snapshot, o commit anterior pode já estar durável
mesmo que a compactação falhe. O processo não tenta continuar da imagem antiga:
writer fica envenenado, router fatal e conexões fechadas. Investigue e reinicie
com replay; não remova o WAL para desbloquear o serviço.

[OASIS §§4.3.2/4.3.3/4.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
define ownership e ACKs; fsync é o contrato local do XMQR. QoS1 permite
retransmissões. Nenhum ACK MQTT garante processamento de negócio.

## Compatibilidade e limites

Não mudam wireMQTT3.1.1, WAL/snapshot1, documentoMQTT2/leitura1, quotas,
defaultsTLS/mTLS, ACL, dependências ou MIT. Sem instrumentação de falhas nos
binários de release. Não há prova de disco físico cheio, energia, cache volátil,
todos os filesystems, MSRV1.88 exato ou brokerWindows nativo.

Fuzzing/B07, ensaios prolongados, matrizB08 e melhoriasC07 continuam pendentes.
Gates e falhas intermediárias reais estão no [registroP86](../prompts/registros/P86-falhas-disco.md).
Distribuição do commit aceito é tarefa [P87](../prompts/broker/87-release-0.11.5.md).

Distribuição concluída: [v0.11.5](https://github.com/licodevone/xmqr/releases/tag/v0.11.5),
com18anexos cujo tamanho/SHA256 remoto foi conferido, .debUbuntu26amd64 e
Hubbroker/admin0.11.5. [Registro de publicação](../prompts/registros/P87-release-0.11.5.md).
[Resumo verificável emJSON](results/p87-aceite-publicacao-2026-10-13.json).
