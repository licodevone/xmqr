# Histórico de versões

## 0.37.0 — cabeçalhos MQTT 5 reservados (experimental)

- P203: tipo de controle zero reservado após CONNACK recebe DISCONNECT `0x81`.
- P204: AUTH com flags reservadas não zero recebe DISCONNECT `0x81`, antes do corpo.
- P205: corrige P178; PINGREQ/DISCONNECT com flags reservadas não zero passam de `0x82` para o motivo malformado `0x81`. A release 0.36.0 conserva o comportamento antigo.

Documento durável v15 sem migração. Client independente 0.30.0 e admin independente 0.10.0 permanecem. Fases globais 6A–6D/7–9 e matriz MQTT 5 continuam abertas.

## 0.36.0 — diagnóstico de pacotes MQTT 5 adicionais (experimental)

- P199: CONNECT inicial com bloco de propriedades íntegro, mas campos seguintes truncados ou extras, recebe CONNACK `0x81` quando o limite permite, antes de criar sessão ou Will.
- P200: flags reservadas inválidas de SUBSCRIBE, UNSUBSCRIBE e PUBREL após CONNACK recebem DISCONNECT `0x81` sem aplicar estado parcial.
- P201: CONNACK, SUBACK, UNSUBACK e PINGRESP exclusivos do servidor enviados pelo client após CONNACK recebem DISCONNECT `0x82` antes de interpretar o corpo.

Documento durável v15 sem migração. Client independente 0.30.0 e admin independente 0.10.0 não mudam. Fases globais 6A–6D/7–9 e a matriz MQTT 5 permanecem abertas.

## 0.35.0 — erros de sequência e formato MQTT 5 (experimental)

- P194: um segundo CONNECT após CONNACK MQTT 5 recebe DISCONNECT `0x82` antes de trocar a sessão.
- P195: texto UTF-8 malformado ou U+0000 após CONNACK recebe DISCONNECT `0x81` nos contextos decodificados.
- P196: texto inválido no CONNECT/Will inicial MQTT 5 recebe CONNACK `0x81` antes de criar sessão ou Will, respeitando Maximum Packet Size.
- P197: campos internos truncados, inteiro variável interno inválido e bytes extras em pacote fechado após CONNACK recebem DISCONNECT `0x81` sem aplicação parcial.

O documento durável permanece v15, sem migração. Client independente 0.28.0 e admin independente 0.10.0 permanecem. As fases 6A–6D/7–9 e a matriz MQTT 5 global continuam abertas.

## 0.34.0 — diagnósticos MQTT 5 adicionais (experimental)

- P183/P184: CONNECT/Will com propriedades inválidas recebe CONNACK `0x81`/`0x82` antes de criar sessão.
- P185–P187: PUBLISH, AUTH, DISCONNECT e ACKs QoS classificam propriedades impróprias/duplicadas com DISCONNECT `0x81`/`0x82` nos casos documentados.
- P188/P189: Packet Identifier zero nos ACKs QoS e comandos SUBSCRIBE/UNSUBSCRIBE/PUBLISH QoS 1/2 recebe DISCONNECT `0x82` antes de alterar estado.
- P190: PUBLISH com QoS reservado 3 recebe `0x81`; QoS 0 com DUP ligado recebe `0x82`.

O documento durável permanece v15, sem migração. Client independente 0.28.0 e admin independente 0.10.0 permanecem. A matriz MQTT 5 e as fases 6A–6D/7–9 continuam abertas.

## 0.33.0 — propriedades de assinatura MQTT 5 (experimental)

- P180: SUBSCRIBE/UNSUBSCRIBE aceitam User Property repetível com limites locais e rejeição atômica; o estado durável segue v15.
- P181: após CONNACK MQTT 5, propriedade imprópria de assinatura envia DISCONNECT `0x81` e Subscription Identifier duplicado envia `0x82`.

A matriz MQTT 5 e as fases 6A–6D/7–9 continuam abertas.

## 0.32.0 — diagnósticos de encerramento MQTT 5 (experimental)

- P174: DISCONNECT de erro permitido ao client encerra com Will; motivos exclusivos do servidor são recusados.
- P175: quadro acima do teto local recebe DISCONNECT `0x95` após CONNACK MQTT 5.
- P176: Topic Alias zero, acima do anunciado ou desconhecido recebe DISCONNECT `0x94` sem publicação.
- P177: Remaining Length com quatro bytes de continuação recebe DISCONNECT `0x81`.
- P178: flags fixas inválidas de PINGREQ/DISCONNECT recebem DISCONNECT `0x82`.

O documento durável permanece v15; matriz normativa MQTT 5 e fases 6A–6D/7–9 continuam abertas.

## 0.31.0 — motivos MQTT 5 e interoperabilidade (experimental)

- P172: DISCONNECT MQTT 5 `0x04` publica Will pela transição durável, incluindo atraso e restart; `0x00` continua cancelando.
- P171: PUBREL/PUBCOMP aceitam `0x92` e diagnósticos válidos; PUBCOMP libera a tentativa QoS2.
- P170: PUBREC negativo válido do assinante MQTT 5 encerra a tentativa QoS2 sem PUBREL, libera quota e persiste a remoção; parser aceita diagnósticos opcionais e rejeita motivos/propriedades inválidos. Sem tag/release isolada.
- P169: PUBACK negativo válido do assinante MQTT 5 conclui a tentativa QoS1, libera inflight e preserva a conexão; parser aceita Reason String única e User Property repetida, rejeita códigos/propriedades inválidos. Sem tag/release isolada.
- P168: Eclipse Paho Python 2.1.0 amplia o gate externo de MQTT 5 para ID atribuído, sessão, QoS0/1/2 e retained, junto ao Mosquitto.

## 0.30.0 — Client Identifier atribuído no MQTT 5 (experimental)

- P166: CONNECT MQTT 5 com Client Identifier vazio recebe ID aleatório exclusivo e propriedade obrigatória `0x12` no CONNACK; colisão é resolvida no ator e limite de pacote insuficiente recusa antes do commit. MQTT 3.1.1 continua recusando ID vazio. C97–C99 formam o fluxo de CLI e reconexão manual.

## 0.29.0 — Will MQTT 5 e estado v15 (experimental)

- P164: Message Expiry Interval do Will MQTT 5 é persistido como intervalo pendente; o deadline começa na publicação efetiva, inclusive após Will Delay, restart/crash e encerramento administrativo. Estado v15 lê v1–v14; broker 0.28.0 rejeita v15. Admin 0.9.0 transporta backup bruto, mas A19 atualiza o core antes da release. Rollback executável requer backup privado v14.
- P163: Will MQTT 5 aceita Payload Format Indicator, Content Type, Response Topic, Correlation Data e User Property ordenada, inclusive com Will Delay; os metadados atravessam publicação, retained, fila offline e restart no estado v14. Message Expiry do Will ainda está fora do recorte.
- P162: limite opcional de Keep Alive MQTT 5 por TOML/ambiente; quando reduz o valor pedido no CONNECT, anuncia Server Keep Alive no CONNACK e usa o mesmo valor para o timeout. Recusa orçamento de CONNACK insuficiente antes da sessão. MQTT 3.1.1 e ausência da opção preservados.

## 0.28.0 — SASL PLAIN e reautenticação MQTT 5 (experimental)

- P160: broker aceita AUTH MQTT 5 `0x19` para reautenticação PLAIN na mesma identidade em TLS/mTLS, responde AUTH `0x00` com método confirmado ou DISCONNECT `0x86` em falha de credencial. Método/propriedades/motivo inválidos encerram sem alterar a sessão. Client C92 pode iniciar reautenticação explícita antes de pub/sub.
- P159: autenticação inicial SASL PLAIN com Authentication Method/Data em CONNECT MQTT 5 sobre TLS e confirmação do método no CONNACK, sem credenciais convencionais no mesmo pacote. Erros de TLS, formato, segredo e limite de resposta são recusados sem abrir sessão.
- P158: CONNECT MQTT 5 com Authentication Method desconhecido recebe recusa específica 0x8C; Authentication Data órfã/duplicada/truncada é erro, sem criar sessão.

O estado durável segue v14, compatível com admin independente 0.9.0. Desafio AUTH e reautenticação periódica continuam ausentes; fases 6A–6D e 7–9 seguem abertas.

## 0.27.0 — redistribuição QoS1 compartilhada e estado v14 (experimental)

- P156: ao terminar a sessão escolhida, uma cópia QoS1 compartilhada ainda sem PUBACK pode ser entregue a outro membro elegível do grupo. A origem durável permite recalcular QoS, Retain As Published e Subscription Identifier para o novo membro. Sem outro membro ou capacidade, a cópia é descartada; QoS2 iniciado continua vinculado à sessão escolhida.
- O documento durável migra de v13 para v14 na próxima gravação. Broker 0.26.0 e admin independente 0.8.0 não abrem v14; rollback requer backup privado v13 anterior à migração. O client independente 0.24.0 permanece parceiro. AUTH e fases globais 6A–6D/7–9 continuam abertas.

## 0.26.0 — shared subscriptions MQTT 5 e estado v13 (experimental)

- P152: na base 0.25.0, CONNACK MQTT 5 anunciava Shared Subscription Available=0 (0x2A) e SUBSCRIBE `$share/` recebia DISCONNECT 0x9E; o anúncio exigia espaço no Maximum Packet Size.
- P153: CONNACK passa a anunciar disponibilidade=1; grupos temporários ativos distribuem uma cópia por grupo/filtro, sem retained inicial e com cópia normal independente.
- P154: grupos de sessão persistente passam ao documento v13; QoS1/2 pode ser atribuído a membro offline quando não há ativo, e QoS2 já iniciado volta à sessão escolhida após reinício. A recomendação de redistribuir QoS1 após término da sessão ainda não é atendida. AUTH e fases globais continuam abertos. Backup privado v12 é necessário para voltar a broker 0.25.0/admin independente 0.7.0.

## 0.25.0 — Subscription Identifier MQTT 5 (experimental)

- P150: SUBSCRIBE MQTT 5 aceita Subscription Identifier 1..268435455; guarda o valor por filtro no documento durável v12 e envia os IDs correspondentes nos PUBLISH QoS0/1/2, retained, offline e após restart. Filtros sobrepostos preservam IDs duplicados. Client não pode enviar a propriedade em PUBLISH. O admin independente 0.6.0 ainda não abre v12; rollback exige backup privado v11 anterior à migração.

## 0.24.0 — opções de assinatura MQTT 5 e estado v11 (experimental)

- P146: sessão MQTT 5 retomada com quota durável QoS2 cheia responde PUBREC `0x97` a novo packet ID sem perder a transação anterior; duplicata já aceita e PUBREL continuam, e uma publicação nova passa após liberar a vaga. O documento durável segue v10.
- P147: SUBSCRIBE MQTT 5 aceita Retain Handling 0/1/2 por filtro; o valor 1 consulta a existência da assinatura na sessão persistida e 2 não envia retained no SUBSCRIBE. No Local e Retain As Published continuam fora do recorte. Sem migração do estado v10.
- P148: No Local e Retain As Published por filtro MQTT 5, inclusive filtros sobrepostos e sessão retomada; documento durável v11 na próxima gravação. O admin independente 0.5.0, com core 0.23.0 pinado, ainda não abre v11.

## 0.23.0 — limite de recepção MQTT 5 no CONNACK, experimental

- P144: o broker anuncia Receive Maximum 1..32 conforme a quota `MQTT_MAX_INFLIGHT` quando o CONNACK cabe no Maximum Packet Size do client. Os limites de pacote 5..7 e 10..15 mantêm o fallback anterior e omitem essa propriedade. Documento durável permanece v10; a fase 6C global continua aberta.

## 0.22.0 — metadados de publicação MQTT 5, experimental

- P141: Payload Format Indicator (0/1) e Content Type MQTT 5 (até 256 bytes) são preservados na entrega, retenção, fila offline e replay. O documento durável passa a v9 na próxima gravação; rollback para 0.21.0 exige backup privado v8. O broker não valida a codificação UTF-8 do payload quando o indicador é 1, opção permitida ao receptor pelo MQTT 5.
- P142: Response Topic, Correlation Data binária e User Property repetível são preservados em QoS0/1/2, retained e fila offline. Documento durável v10; rollback a 0.21.0 exige backup privado v8 anterior à primeira gravação P141/P142.

## 0.21.0 — Topic Alias MQTT 5, experimental

- P138: Topic Alias de entrada MQTT 5 por conexão, com máximo anunciado de 16 quando o CONNACK cabe; alias inválido ou não estabelecido fecha a conexão sem publicar.
- P139: Topic Alias de saída MQTT 5 limitado pelo máximo anunciado pelo assinante (e pelo teto local de 16); primeira entrega estabelece o alias e as seguintes usam tópico vazio. Associação reinicia por conexão, inclusive após restart; sem alias em MQTT 3.1.1 ou máximo zero. O Mosquitto 2.0.22 encerra após a forma abreviada válida, reproduzida isoladamente.

## 0.20.0 — limites de fluxo MQTT 5, experimental

- P134: Receive Maximum do assinante limita PUBLISH QoS1/2 vivos, retidos, offline e em replay sem limitar QoS0 ou PUBREL.
- P136: Maximum Packet Size do assinante limita cada pacote enviado; PUBLISH grande demais é descartado e sua obrigação QoS é concluída duravelmente.
- O documento durável permanece v8; fases 6A–6D e conformidade MQTT 5 integral continuam abertas.

## 0.19.0 — expiração e Will MQTT 5, experimental

- P132: Will MQTT 5 com Will Delay opcional; publicação/cancelamento duráveis, restart e migração de estado v7 para v8. Falha do WAL ao agendar Will encerra o ator para recuperar obrigação anterior.
- P131: Session Expiry no DISCONNECT normal MQTT 5, com transição durável e rejeição de zero→positivo.
- P130: Message Expiry no PUBLISH MQTT 5, limpeza de retidos/offline e encaminhamento do intervalo restante; migração de v6 para v7.
- Fases 6A–6D ainda abertas; rollback para 0.18.0 requer backup privado do estado v6 anterior à migração.

## 0.18.0 — sessões MQTT 5, experimental

- P128: Session Expiry finita com deadline durável, remoção automática e migração do documento v5 para v6; leitura v1–v5. Crash com conexão ativa inicia o intervalo na recuperação para não descartar dados aceitos sem instante de fechamento conhecido.
- P127: Clean Start separado de Session Expiry zero/infinita; Session Present real, assinatura e QoS offline recuperados após restart.
- P126: ACKs de sucesso PUBACK/PUBREC/PUBREL/PUBCOMP e DISCONNECT normal MQTT 5 aceitam Reason Code `0x00` explícito e comprimento de propriedades zero, preservando as formas abreviadas. Motivos de erro e propriedades continuam fora do subconjunto.

## 0.17.0 — MQTT 5 ampliado, experimental

- P125: libera explicitamente o lock de escritor ao encerrar `Store`, após recorrência de `AlreadyOpen` no teste de snapshot; exclusão e recuperação preservadas.
- P123: CONNECT MQTT 5 aceita Request Problem/Response Information, Topic Alias Maximum e User Property informativos, com validação de duplicatas, valores e UTF-8; sem eco, armazenamento ou aliases enviados.
- P122: PUBLISH/SUBSCRIBE MQTT 5 QoS2 com ciclo PUBREC/PUBREL/PUBCOMP e entrega cruzada; CONNACK omite Maximum QoS (padrão 2). ACL negada em QoS2 responde PUBREC `0x87` sem commit.
- P121: UNSUBSCRIBE MQTT 5 sem propriedades e UNSUBACK com motivo por filtro (`0x00` removido, `0x11` inexistente); remoção confirma somente após commit, ausência não grava estado. MQTT 3.1.1 preservado.
- P120: SUBACK MQTT 5 usa `0x87` para filtro negado por ACL, sem commit quando todos os filtros são recusados; MQTT 3.1.1 mantém `0x80`.
- P119: recusa ACL de PUBLISH MQTT 5 QoS 1 retorna PUBACK `0x87` sem commit; a conexão continua disponível para publicação permitida. MQTT 3.1.1 mantém o fechamento anterior.
- P118: falha intermitente `AlreadyOpen` em teste de snapshot investigada; rerun remoto e repetições locais passaram, sem mudança de persistência.

## 0.16.0 — MQTT 5 inicial, experimental

- P116: SUBSCRIBE MQTT 5 QoS0/1 sem propriedades avançadas, SUBACK com
  reason code por filtro e entrega de mensagens vivas/retained em PUBLISH 5;
  PUBACK de assinante QoS1, testes cruzados e Mosquitto externo.
- P115: broker aceita publicação MQTT 5 QoS0/1 com sessão limpa, Receive
  Maximum opcional no CONNECT e PUBLISH sem propriedades; CONNACK anuncia
  QoS máximo 1 e pacote máximo 64 KiB. Teste cruzado
  com assinante 3.1.1; demais recursos MQTT 5 seguem pendentes.
- P114: um `CONNECT` MQTT 5 recebe recusa parseável `CONNACK 0x84` no formato
  MQTT 5 e a conexão é fechada sem criar sessão ou alterar o estado. Esse
  comportamento histórico foi substituído por P115.
- MQTT 3.1.1 e o documento durável v5 permanecem iguais. A fase 6A integral
  continua aberta.

## 0.15.0 — operação administrativa local, experimental

- P107–P112: canal Unix autenticado, aplicação online de bundle, recibos
  duráveis, inventário/ações de sessão e retained, auditoria rotacionável e
  métricas administrativas; [aceite da fase 5](docs/phase5-acceptance.md).
- O documento durável MQTT v5 lê v1–v4; versões antigas não leem v5. Para
  rollback, conservar backup offline anterior e diretório de estado separado.
- P113: tag/prerelease `v0.15.0` com pacotes, hashes e limites publicados.

## 0.14.0 — rotação TLS e ACL estática por endpoint, experimental

- P100/B11: SIGUSR1 valida certificado, chave, CA e CRL completos e publica
  uma geração comum aos endpoints mTLS para novos handshakes; falha conserva
  a anterior. TLS-senha também gira certificado/chave. Conexões ativas seguem
  até encerramento próprio ou controlado.
- P101/B09: `[[endpoint_policies]]` associa arquivos de usuários/ACL estáticos
  a cada bind mTLS. Principal, client ID e perfil durável são isolados por
  endpoint; roteador, estado, quotas e TLS permanecem compartilhados.
- P102/E02: campanha física na ESP32 COM4 passou com seis rotações TLS:
  rejeição de chave inválida, novo certificado, rejeição/recuperação de CA e
  revogação/recuperação por CRL. Fase 4 aceita no escopo finito documentado.

## 0.13.1 — correção de distribuição do B10

- P99: alinha o `ARG VERSION` padrão do Dockerfile ao Cargo. Nenhuma alteração
  de TLS/MQTT. A tag0.13.0 de código não teve release por falha no contrato de
  distribuição; a publicação usa este patch com novo commit e tag.

## 0.13.0 — TLS com senha e ACL, experimental

- P97/B10: modo `tls-password` opt-in com certificado do servidor e CONNECT
  autenticado por usuário/senha, ACL deny-by-default e estado separado.
- Integração client C48: QoS0/1/2 e negativos de senha, CA, SAN e ACL.
  Configuração recusa client CA/CRL; mTLS continua padrão.
- B09 políticas por endpoint, B11 rotação e E02 físico ainda pendentes.

## 0.12.0 — endpoints mTLS compartilhados, experimental

- P96: até três endpoints adicionais via TOML v1, com política, roteador,
  estado, limite de conexões e IDs compartilhados. Apenas secure-mtls; restart
  para alterar binds. Políticas distintas por endpoint continuam pendentes.
- Integração real com client de perfis: QoS0/1/2 cruzados, retained após
  restart, N/N+1 agregado, bind ocupado e negativos de CA/credenciais.
- MQTT3.1.1, formatos duráveis e limites existentes preservados.

## 0.11.6 — robustez da fase3, experimental

- CONNECT com nível não suportado responde CONNACK0x01; identificador vazio
  ou acima da quota local256bytes responde0x02, SessionPresent0 e encerra
  antes de registro/commit/pipeline. Malformados continuam fechando sem ACK.
- P95: encerramento TLS limitado mesmo após erro de cleanup; parada aguarda
  conexões admitidas e actor/writer no mesmo prazo total de 15s, preservando
  o erro de armazenamento. Gates finais nativos/TLS/wire/campanhas PASS.
- P90/B07: corpus sintético, mutações estáveis com oráculos/watchdog e
  regressões; não equivale a LibFuzzer/ASAN ou cobertura guiada.
- P91/B08: ensaios prolongados TCP/mTLS, recuperação/pressão, matriz wire
  normativa einterop Mosquitto2.0.22:6soak/87interop/19wire/12TLS PASS, com
  limites/falhas históricas no aceite da fase3.
- Binários/pacotes preservam MIT e textos originais LICENSE/NOTICE de
  terceiros, incluindo AWS-LC vendorizado; inventário não é composição ELF.
- Client0.9.0 independente traz C45; admin independente0.1.0 não repinado.
  Sem formatos/dependências/quotas novas, sem MQTT5 ou prontidão de produção.

## 0.11.5 — recuperação: erro de leitura não é cauda incompleta

- Erro ao completar o tamanho de um registro WAL agora é propagado; somente
  UnexpectedEof permite truncar uma cauda interrompida. Evita perda de evidência
  por confundir EIO com fim de arquivo durante recuperação.
- P86/B06: falhas por instância apenas em cfg(test), ENOSPC/EIO/write-zero,
  escrita curta/Interrupted, snapshot/compactação e corrupção; frames TCP
  independentes verificam ausência de PUBACK/PUBREC/PUBCOMP após falha.
- MQTT3.1.1, perfis/ACL, quotas, dependências/MIT e formatos duráveis mantidos.
- Fase3 em andamento: fuzzing, testes prolongados e matriz externa ampliada
  continuam pendentes; injeção não prova disco físico cheio ou perda de energia.

## 0.11.4 — encerramento limitado de cliente TLS lento

- Shutdown/flush de transporte tem deadline3s, liberando tarefa e admissão
  quando um cliente mTLS deixa de ler e impede o fechamento da conexão.
- Regressões de fila limitada, recusa sem fan-out/retained parcial e timeout.
- Campanha de saturação e matriz externa por P80/C43; placa ESP32 permanece
  gate físico independente, sem declarar fase2 concluída por estes testes.
- Quotas, MQTT3.1.1, perfis de segurança, dependências/MIT e WAL preservados.

## 0.11.3 — admin e distribuição Docker Hub

- Admin --version/-V consulta a versão sem configuração, rede ou estado.
- Alvo Docker admin separado; broker continua como alvo padrão com ambos os binários.
- Contexto Docker allowlist; conferência da versão real na construção.
- .deb Ubuntu26 amd64 inclui broker/admin; imagens Bookworm amd64 são distintas.
- Exportação/checksums/manifesto de commit e plano detalhado de paridade concluído.
- Sem alterações de MQTT, quotas, segurança ou formato de persistência.

## 0.11.2 — consulta de versão

- --version/-V como argumento único, antes de runtime/logs/configuração/estado.
- Argumentos não suportados recusados exit2 sem echo; startup sem argumentos mantido.
- Dockerarchive/hash e debUbuntu26amd64 porrelease; client permanece0.7.1.


## 0.11.1 — distribuição Docker

- LabelsOCI/version/revision, SIGTERM e imagemLinux/amd64 exportada comchecksum.
- mTLS pub/sub, retained/restart e negativos em containers isolados aprovados.
- Pacote.debUbuntu26 porrelease, com install/upgrade/rollback testado.
- Sem alterações funcionais de protocolo, TLS ou quotas.


## 0.11.0 — fase1: configuração e quotas

- P58: teto64KiB uniforme do pacote completo, incluindo cabeçalho; negativos
  de framing e payload4096/4097. Validação completa Ubuntu26 emP61.

- P55: quotas lógicas configuráveis com recuperação/commit coerentes e redução
  incompatível recusada; aceite Unix aprovado emP61.

- P54: limite de conexões TCP configurável em TOML ou MQTT_MAX_CONNECTIONS,
  faixa1..64; default64 e quotas duráveis preservados.

- P52: configuração TOML versionada via MQTT_CONFIG, com overrides legados,
  caminhos relativos, validação estrita e erros sem conteúdo sensível.
- Configuração imutável durante a execução; alterações exigem restart.

- P61:103 testes broker e52 client; interopMosquitto, mTLS/systemd e shutdown;
  pacote Ubuntu26 testado em install/upgrade/rollback/remove/purge.
- Estado, defaults e configurações existentes preservados; release experimental.

## 0.10.0 — systemd e Ubuntu 26.04

- Tratamento SIGTERM/SIGINT e integração com systemctl.
- Pacote .deb amd64 para Ubuntu26.04, sem ativação automática.
- Configuração e dados preservados; guia de instalação, upgrade e remoção.
- Release experimental com pacote e SHA-256; sem repositório APT próprio.
- Parada durável: Wills, sessões, snapshot e shutdown do writer.
- Evidência: prompts/registros/P47-systemd-ubuntu.md.

## Histórico dos marcos anteriores

# Histórico de versões

## 0.9.0 — tag publicada v0.9.0

- P45: `mqtt-admin state backup|verify|restore` para o estado durável MQTT offline.
- P46: imagem Docker Debian slim multi-stage, com usuário sem privilégios, broker
  e `mqtt-admin`; imagem local `xmqr-broker:0.9.0`, sem envio a registry.
- Backup compacta o WAL, guarda manifest TOML e SHA-256; verify testa recuperação
  em cópia temporária; restore só publica num diretório novo e nunca sobrescreve.
- Arquivos 0600 e diretórios 0700 em Unix. Bundle dinâmico, TLS e configuração
  externa não estão incluídos; backup/restore durável requer Linux/WSL.
- Evidências: `prompts/registros/P45-0.9.0.md` e `P46-docker.md`;
  gates Linux/WSL e build Docker aprovados.



O projeto segue versionamento semântico. Enquanto a conformidade e a operação

de produção não passarem pelo gate de release, a série permanece `0.x`.

Mudanças incompatíveis ainda podem ocorrer nela. `1.0.0` exigirá testes de

interoperabilidade independentes, recuperação após falhas, revisão de segurança

e documentação de operação; versões `1.x` manterão compatibilidade prometida,

e `2.0.0` indicará quebra dessa compatibilidade.



## 0.8.0 — tag publicada v0.8.0



- Bundle privado opt-in com usuários, grupos, papéis e ACL; reload Linux por

  SIGHUP com commit antes da publicação da política e reautenticação obrigatória.

- Revogação de assinaturas, filas e Will; preservação de inbound QoS 2 aceito.

- Auditoria sem segredos; mesmos limites, dependências e formato durável.

- Interface e limitações em docs/security/dynamic-security.md; gates no registro P44.



## 0.7.0 — tag publicada v0.7.0



- Monitoramento HTTP opcional, somente loopback: health, readiness por probe

  real do ator/writer e métricas Prometheus com labels finitos.

- Contadores de conexões, mensagens QoS, rejeições, commits/latência/snapshots

  e Will; gauges agregados de filas/sessões/retained. Sem novas dependências.

- HTTP limitado a 16 handlers, header 4096 bytes, read/write 1 s e probe 500 ms.

- Documento durável, quotas e MIT preservados. Não há release 0.7 aprovada;

  resultados e bloqueios estão no registro P43.



## 0.6.0 - tag v0.6.0 local/remota verificada



- Last Will MQTT3.1.1 duravel com QoS0/1/2, payload binario, retain, ACL e

  limite1024 bytes UTF-8. Queda, timeout, protocolo, takeover e cancelamento

  da task publicam; DISCONNECT cancela duravelmente.

- Retained existente revisado: substituicao, exclusao vazia, wildcard e restore.

- Documento MQTT v2 com leitura v1 e pending_wills; WAL/snapshot continuam v1.

  Rollback somente com backup completo anterior; nenhum estado real migrado.

- Cliente proprio recebe --will-topic/message/qos/retain. Script independente

  scripts/verify_last_will.py verifica ciclo de vida, restart e CLI sem Mosquitto.

- Lints assert_is_empty preexistentes de store e teste admin corrigidos.

- Linux/WSL Rust1.99:81 testes e9 integracoes PASS; fmt/Clippy/inventario/build

  PASS. Mosquitto e TLS/mTLS externo nao executados; sem conformidade integral.



## 0.5.0 - tag v0.5.0 verificada



- Filtros MQTT 3.1.1 `+` e `#`, níveis vazios e tópicos `$` explícitos;

  nomes de publicação e filtros são tipos distintos, validados também no restore.

- Uma entrega por cliente para filtros sobrepostos, no maior QoS aplicável,

  incluindo deduplicação de mensagens retidas no mesmo SUBSCRIBE.

- ACL exige literalmente o filtro solicitado; tópicos concretos são

  revalidados no fan-out e na recuperação de filas offline/inflight.

- Script reproduzível com clientes Mosquitto para QoS 0/1/2, retained,

  reinício, sessão persistente, UNSUBSCRIBE e pacotes inválidos, incorporado ao CI.

- Inventário verificável das licenças declaradas das dependências, mantendo

  o código XMQR sob MIT e os direitos dos componentes de terceiros.

- O formato de estado permanece na versão 1. A 0.4 lê estados antigos,

  mas não entende assinaturas wildcard produzidas pela 0.5: antes do retorno,

  remova-as com UNSUBSCRIBE ou restaure um backup completo anterior.

- Tópicos e filtros aceitam até 1024 bytes UTF-8, com limite compartilhado

  entre broker e CLI; fronteiras ASCII/multibyte, wire, ACL e restore têm testes.

  O formato v1 permanece, mas snapshots anteriores com limite 256 não restauram

  nomes longos: preserve backup anterior completo para retorno.

- Limites continuam explícitos: 1024 bytes por tópico/filtro, 256 assinaturas

  por sessão e 64 sessões. Last Will, escala e operação de produção continuam pendentes.



## 0.4.0 — 2026-09-24



- Etapas didáticas `password-lab` e `acl-lab`, sem TLS e restritas a loopback,

  para introduzir autenticação e autorização separadamente.

- Usuários de laboratório podem usar somente senha, sem fingerprint ou

  certificado; `secure-mtls` continua exigindo os três fatores.

- `mqtt-admin user create|list|update-password|delete` com lock, arquivo

  temporário `0600`, validação, rename atômico e sincronização durável.

- Roteiro executável para acesso aberto, senha, ACL, tópico permitido/negado e

  administração de usuários; TLS permanece etapa posterior.



## 0.3.0 — 2026-09-24



- Modo didático explícito `MQTT_MODE=open-lab`, limitado a loopback, para

  demonstrar MQTT 3.1.1 QoS 0 sem TLS, autenticação ou ACL.

- Cliente de laboratório com `--open-lab`, sem certificados ou prompt de senha.

- Separação dos diretórios de estado por perfil, impedindo que o laboratório

  aberto reutilize ou remova sessões do modo seguro.

- Roteiro inicial de três terminais para publicar e receber dados manualmente.



## 0.2.0 — 2026-09-23



- MQTT 3.1.1: QoS 1/2 nos dois sentidos, `PUBACK`/`PUBREC`/`PUBREL`/`PUBCOMP`,

  `UNSUBSCRIBE`, mensagens retidas e sessões persistentes com `CleanSession=0`.

- Estado MQTT versionado no WAL existente; commit com `fsync` antes dos ACKs

  que transferem responsabilidade, quotas e snapshots periódicos.

- Cliente de laboratório com `--qos`, `--retain` e `--clean-session`.

- Não é uma declaração de conformidade MQTT 3.1.1 completa ou prontidão de

  produção: Will, filtros wildcard, testes externos de interoperabilidade,

  escala e operação ainda precisam de trabalho.



## 0.1.0 — base inicial



- Transporte TLS/mTLS, autenticação usuário/senha com vínculo ao certificado,

  ACL de tópicos exatos e fluxo MQTT QoS 0.



## Registro histórico P43



2026-10-08:72 testes Unix, fmt/Clippy/inventário/build e6 integrações monitoring

mais9 regressões Will PASS, com cliente independente baseline26c1019. Seis

recusas de configuração reais também PASS. Histórico de bloqueios anteriores

não descreve o estado atual. Mosquitto/TLS/mTLS externo NOT_RUN. Aguardar

publicação do mantenedor; ver registro P43. Nenhuma implementação0.8 executada.

### Correção local P55 rev3 (aceite Unix pendente)

- Last Will saturada encerra o ator/conexões e preserva a obrigação durável;
  takeover não pode substituir a Will não publicada.
- Recuperação que falha ao publicar Will/commit aguarda encerramento do writer.
- Novos negativos de startup real v1/v2 e harness isolado de quotas/replay/CLI;
  execução durável Linux/WSL ainda pendente, sem novo marco de release.
