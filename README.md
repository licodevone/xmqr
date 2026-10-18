# XMQR

O candidato experimental 0.41.0 inclui P214: WSS mTLS
fora de loopback somente com `MQTT_WSS_BIND` remoto e
`MQTT_WSS_REMOTE_ENABLED=true` (ou campos TOML equivalentes). A mesma
política de certificado cliente, credenciais e ACL continua exigida; o
certificado servidor precisa cobrir o nome usado pelo client. Acesso pelo
navegador continua pendente. [Prompt P214](prompts/broker/214-remote-wss-mtls-bind.md)
e [aceite parcial](prompts/registros/P214-remote-wss-mtls-bind.md).

A prerelease experimental 0.40.0 reúne P212: `MQTT_WSS_BIND` adiciona WSS mTLS
opcional somente em loopback, com certificado cliente, usuário/senha e ACL.
O listener compartilha quota, router e rotação TLS com o TCP seguro e recusa
`Origin`. C114 aceitou o client WSS local, distribuído no marco independente
0.33.0. A prerelease 0.39.0 abaixo ainda não inclui P212; acesso remoto,
navegador e aceite global da fase 7 permanecem pendentes.
[Prompt P212](prompts/broker/212-mtls-websocket-listener.md) e
[registro](prompts/registros/P212-mtls-websocket-listener.md).
[Release](https://github.com/licodevone/xmqr/releases/tag/v0.40.0),
[nota](docs/releases/0.40.0.md) e [registro P213](prompts/registros/P213-release-0.40.0.md).

A prerelease experimental 0.39.0 distribui P210: listener WebSocket MQTT opt-in `MQTT_WS_BIND`
somente no perfil `open-lab`. Exemplo local: `MQTT_MODE=open-lab
MQTT_BIND=127.0.0.1:1883 MQTT_WS_BIND=127.0.0.1:8083
MQTT_STATE_DIR=/caminho/privado mqtt-broker`; o caminho é `/mqtt` e o
subprotocolo exigido é `mqtt`. As portas TCP e WS compartilham
`MQTT_MAX_CONNECTIONS`. Handshakes de navegador com `Origin` são recusados.
[Prompt](prompts/broker/210-loopback-websocket-listener.md)
e [registro](prompts/registros/P210-loopback-websocket-listener.md). [Release](https://github.com/licodevone/xmqr/releases/tag/v0.39.0),
[nota](docs/releases/0.39.0.md) e [registro P211](prompts/registros/P211-release-0.39.0.md). WSS,
listener remoto e fase 7 completa ainda não foram aceitos.

Versões e pacotes atuais para Ubuntu 26.04/WSL: [guia de releases e instalação](docs/current-releases-wsl.md).

A prerelease experimental 0.38.0 reúne P207/P208: CONNECT inicial MQTT 5 com flags
reservadas recebe CONNACK `0x81` quando o corpo permite identificar a versão;
PUBACK/PUBREC/PUBCOMP com flags reservadas recebem DISCONNECT `0x81`. Estado
durável v15 sem migração. [Release](https://github.com/licodevone/xmqr/releases/tag/v0.38.0),
[nota](docs/releases/0.38.0.md) e [registro P209](prompts/registros/P209-release-0.38.0.md).
Fases globais abertas.

A prerelease experimental 0.37.0 reúne P203–P205: rejeição do tipo de controle
zero e de AUTH com flags inválidas; corrige a resposta MQTT 5 de PINGREQ e
DISCONNECT inválidos para `0x81`. Estado durável v15 sem migração. [Release](https://github.com/licodevone/xmqr/releases/tag/v0.37.0),
[nota](docs/releases/0.37.0.md) e [registro P206](prompts/registros/P206-release-0.37.0.md).
Fases 6A–6D/7–9 abertas.

A prerelease experimental 0.36.0 reúne P199–P201: CONNECT estruturalmente
inválido, flags reservadas de SUBSCRIBE/UNSUBSCRIBE/PUBREL e pacotes MQTT 5
exclusivos do servidor enviados pelo client passam a receber os motivos
documentados. Estado durável v15 sem migração. [Release](https://github.com/licodevone/xmqr/releases/tag/v0.36.0),
[nota](docs/releases/0.36.0.md) e [registro P202](prompts/registros/P202-release-0.36.0.md).
Fases 6A–6D/7–9 abertas.

A prerelease experimental 0.35.0 reúne P194–P197: segundo CONNECT,
texto UTF-8 malformado antes e depois do CONNACK e comprimentos internos
inválidos recebem os motivos MQTT 5 documentados. O estado durável permanece
v15. O pacote Ubuntu 26.04 amd64, as imagens Docker numeradas e os oito anexos
passaram pelos gates do [P198](prompts/registros/P198-release-0.35.0.md).
[Release 0.35.0](https://github.com/licodevone/xmqr/releases/tag/v0.35.0) e
[nota](docs/releases/0.35.0.md). Fases 6A–6D e 7–9 seguem abertas.

A prerelease experimental 0.34.0 reúne P183–P190: diagnósticos MQTT 5
selecionados para propriedades inválidas, Packet Identifier zero e flags de
PUBLISH impróprias, sem alterar o estado durável v15. Client independente
0.28.0 e admin independente 0.10.0 permanecem. O aceite da distribuição
P192 passou nos gates de distribuição; as fases 6A–6D e 7–9 seguem abertas.
[Release 0.34.0](https://github.com/licodevone/xmqr/releases/tag/v0.34.0),
[nota](docs/releases/0.34.0.md) e
[aceite P192](prompts/registros/P192-release-0.34.0.md).

A release experimental 0.33.0 reúne P180/P181: propriedades User Property repetíveis em
SUBSCRIBE e UNSUBSCRIBE MQTT 5, com limite de 16 pares/2048 bytes e rejeição
antes do roteamento. Identificador de propriedade impróprio recebe DISCONNECT
`0x81`; Subscription Identifier duplicado recebe `0x82`. O estado permanece
v15. O client independente 0.28.0/C102 é o par distribuído; a versão 0.27.0
não expõe essas flags. As fases 6A–6D e 7–9 seguem abertas.
[Release 0.33.0](https://github.com/licodevone/xmqr/releases/tag/v0.33.0),
[nota](docs/releases/0.33.0.md) e [aceite P182](prompts/registros/P182-release-0.33.0.md).

A release experimental broker/admin legado 0.32.0 reúne P174–P178:
DISCONNECT de erro do client com Will e respostas `0x95` para quadro excessivo,
`0x94` para Topic Alias inválido, `0x81` para Remaining Length malformado e
`0x82` para flags fixas inválidas selecionadas. O estado durável permanece
v15, compatível com broker 0.31.0 e admin independente 0.10.0. O client
independente permanece 0.27.0; fases 6A–6D e 7–9 seguem abertas.
[Release 0.32.0](https://github.com/licodevone/xmqr/releases/tag/v0.32.0),
[nota](docs/releases/0.32.0.md) e [aceite P179](prompts/registros/P179-release-0.32.0.md).

A release experimental broker/admin legado 0.31.0 reúne P168–P172:
interop MQTT 5 adicional com Eclipse Paho; PUBACK/PUBREC negativos de assinante;
PUBREL/PUBCOMP `0x92`; DISCONNECT `0x04` que publica o Will. A quota e o
estado durável são preservados nos fluxos testados. O estado continua v15,
compatível com broker 0.30.0 e admin independente 0.10.0. O client independente
permanece 0.27.0. Fases 6A–6D e 7–9 seguem abertas.
[Release 0.31.0](https://github.com/licodevone/xmqr/releases/tag/v0.31.0) e [aceite P173](prompts/registros/P173-release-0.31.0.md).

A release experimental broker/admin legado 0.30.0 distribui P166: o broker atribui um
Client Identifier exclusivo a CONNECT MQTT 5 com ID vazio e anuncia `0x12`
no CONNACK. O client 0.27.0/C97–C99 é o par para receber e reutilizar o ID.
O estado continua v15 e o admin independente 0.10.0 permanece compatível.
As fases 6A–6D e 7–9 seguem abertas. [Release 0.30.0](https://github.com/licodevone/xmqr/releases/tag/v0.30.0) e [aceite P167](prompts/registros/P167-release-0.30.0.md).

A versão 0.30.0 acrescenta P166: CONNECT MQTT 5 com Client Identifier
vazio recebe um identificador novo na propriedade CONNACK `0x12`, preservando
unicidade entre sessões ativas e duráveis. MQTT 3.1.1 ainda recusa ID vazio;
um limite de pacote que não comporte a propriedade obrigatória é recusado
antes de registrar a sessão. O client C97 usa esse modo explicitamente.
[Prompt P166](prompts/broker/166-assigned-client-id-mqtt5.md).

A release experimental 0.29.0 reúne P162–P164: limite configurável de
Keep Alive MQTT 5, metadados do Will e Message Expiry com contagem iniciada
na publicação. O estado durável v15 requer backup privado v14 anterior para
rollback executável ao broker 0.28.0. O client 0.26.0/C94–C95 e o admin
independente 0.10.0/A19 são os parceiros deste marco. Fases 6A–6D e 7–9
continuam abertas. [Release 0.29.0](https://github.com/licodevone/xmqr/releases/tag/v0.29.0) e [aceite P165](prompts/registros/P165-release-0.29.0.md).

A árvore após 0.28.0 também acrescenta P164: `Message Expiry Interval` no
Will MQTT 5 é persistido como intervalo até a publicação efetiva, inclusive
se houver atraso ou recuperação após crash. A partir da publicação, vale o
mesmo prazo de PUBLISH para retained e fila offline. O documento durável passa
a v15 na primeira gravação; broker 0.28.0 não lê v15. O admin 0.9.0 pode
transportar um backup bruto v15, mas seu core antigo não forma um par
homologado com o broker novo. Preserve um backup privado v14 anterior para rollback. A
compatibilidade do novo admin A19 foi aceita no marco 0.10.0.
[Aceite P164](prompts/registros/P164-will-message-expiry-mqtt5.md).

A árvore após 0.28.0 acrescenta P163: o broker aceita no Will MQTT 5
Payload Format Indicator, Content Type, Response Topic, Correlation Data e
User Property ordenada, combináveis com Will Delay. A entrega preserva os
metadados em mensagens imediatas, atrasadas, retidas e na fila offline após
reinício. O client parceiro C94 envia essas propriedades. P163, isoladamente,
mantinha v14 e não incluía Message Expiry do Will; P164 acrescentou ambos no
marco 0.29.0. [Aceite P163](prompts/registros/P163-will-metadata-mqtt5.md).

A árvore após 0.28.0 acrescenta P162: `MQTT_SERVER_KEEP_ALIVE_SECONDS` ou
`[broker].server_keep_alive_seconds` limita opcionalmente o Keep Alive MQTT 5.
Quando o client pede zero ou um valor maior, o broker anuncia `0x13` no
CONNACK e aplica o mesmo prazo; MQTT 3.1.1 não muda. A parcela passou nos
testes e CI e integra a release 0.29.0. [Aceite P162](prompts/registros/P162-server-keep-alive-mqtt5.md).

A versão experimental publicada 0.28.0 reúne P158–P160: MQTT 5 distingue métodos
AUTH indisponíveis, aceita autenticação inicial SASL `PLAIN` somente em TLS e
permite reautenticação AUTH `0x19` da mesma identidade. Uma resposta válida
recebe AUTH `0x00`; senha incorreta ou troca de identidade encerram a conexão.
O client 0.25.0/C92 pode iniciar essa troca explicitamente antes de pub/sub. O modo
convencional continua disponível. O documento durável permanece v14 e o admin
independente 0.9.0 segue compatível. Desafio interativo e reautenticação
periódica não estão implementados; fases 6A–6D e 7–9 continuam abertas.
[Release 0.28.0](https://github.com/licodevone/xmqr/releases/tag/v0.28.0)
e [aceite P161](prompts/registros/P161-release-0.28.0.md).

A versão experimental publicada 0.27.0 inclui P156: redistribuição de cópias
compartilhadas QoS1 não reconhecidas quando a sessão escolhida termina. A
proveniência da cópia migra o documento durável de v13 para v14 na próxima
gravação. O admin independente 0.9.0 lê v14; 0.8.0 lê v13, mas não abre v14.
Preserve backup privado v13 antes da primeira gravação para rollback.
[Release 0.27.0](https://github.com/licodevone/xmqr/releases/tag/v0.27.0)
e [aceite P157](prompts/registros/P157-release-0.27.0.md).

A versão publicada experimental 0.26.0 inclui P153/P154: distribui
`$share/{grupo}/{filtro}` MQTT 5 entre sessões ativas e acrescenta sessão persistente,
fila QoS1/2 sem membro online e retomada QoS2 à sessão escolhida, migrando o
documento durável de v12 para v13 na próxima gravação. Cada grupo recebe uma
cópia por publicação, sem retained inicial; assinatura normal recebe sua cópia
separada. A release 0.25.0 ainda anuncia indisponibilidade e recusa `$share/`
com DISCONNECT 0x9E. Preserve backup offline privado v12 antes de abrir v13:
broker 0.25.0 e admin independente 0.7.0 não o reabrem. O admin independente
0.8.0 lê o estado v13; os três sistemas têm releases numeradas verificadas.
[Release 0.26.0](https://github.com/licodevone/xmqr/releases/tag/v0.26.0)
e [aceite P155](prompts/registros/P155-release-0.26.0.md).

A versão experimental 0.25.0 inclui P150: aceita Subscription Identifier no
SUBSCRIBE MQTT 5 e entrega os IDs correspondentes ao assinante, inclusive em
fila durável e após reinício. O estado passa a v12 na próxima gravação; broker
0.24.0 e admin independente 0.6.0 não reabrem v12; admin 0.7.0 o lê. Preserve backup privado
v11 antes de iniciar esta versão. [Release 0.25.0](https://github.com/licodevone/xmqr/releases/tag/v0.25.0) e [aceite P151](prompts/registros/P151-release-0.25.0.md).

A versão experimental 0.24.0 reúne P146–P148, incluindo No Local e Retain As
Published MQTT 5 com estado durável v11. Pacotes e imagens numeradas estão na
[release 0.24.0](https://github.com/licodevone/xmqr/releases/tag/v0.24.0);
[P149](prompts/registros/P149-release-0.24.0.md) registra os gates. O admin
independente [0.6.0](https://github.com/licodevone/xmqr-admin/releases/tag/v0.6.0)
passou nos testes offline de leitura/backup/restore de v11; 0.5.0 não lê v11.

No marco experimental 0.23.0, P144 anuncia no CONNACK MQTT 5 a quota de
recepção QoS1/2 configurada (1..32) quando há espaço, sem mudar o documento
durável v10. O client parceiro 0.21.0 exibe metadados MQTT 5 em JSONL e repete
publicações em série. [Nota de release](docs/releases/0.23.0.md). A fase 6C
global segue aberta.

No candidato 0.24.0, P146 mantém a sessão MQTT 5 ativa quando
ela é retomada com a quota durável QoS2 cheia: um PUBLISH novo recebe PUBREC
`0x97` (Quota exceeded), sem substituir o QoS2 antigo. A transação anterior
continua por PUBREL e libera espaço para uma publicação posterior. O documento
durável permanece v10 e o limite de recebimento por conexão ainda se aplica.

No candidato 0.24.0, P147 aceita Retain Handling 0/1/2 no
SUBSCRIBE MQTT 5. A opção 1 só envia mensagens retidas quando o filtro ainda
não existe na sessão; a opção 2 não as envia no ato da assinatura. A decisão
usa a assinatura persistida após reinício.

No candidato 0.24.0, P148 aceita No Local e Retain As Published
por filtro MQTT 5, inclusive retomada após restart. O documento durável passa
a v11 na próxima gravação. Antes de migrar, preserve um backup privado v10:
o admin independente 0.5.0 ainda usa o core 0.23.0 e não abre v11. A fase 6D
continua aberta para Subscription Identifier, assinaturas compartilhadas e AUTH.

No marco experimental 0.22.0, P141 preserva Payload Format
Indicator e Content Type de PUBLISH MQTT 5; P142 acrescenta Response Topic,
Correlation Data binária e User Property repetível em ordem. As propriedades
seguem em entregas, mensagens retidas e fila offline. O documento durável
passa a v10 na próxima gravação. Preserve backup privado v9 para rollback ao
P141 e backup v8 para voltar ao broker 0.21.0. O client 0.20.0 publica essas
propriedades. Veja a [nota de release](docs/releases/0.22.0.md). A fase 6C
global segue aberta.

O marco experimental 0.21.0 aceita Topic Alias MQTT 5 de entrada e saída
(P138/P139), limitado a 16 por conexão e ao máximo anunciado pelo assinante.
O client 0.19.0 recebe a forma abreviada. O Mosquitto 2.0.22 fecha a conexão
ao recebê-la em fixture isolada; essa direção externa não está homologada.
Veja a [nota de release](docs/releases/0.21.0.md). A fase 6C segue aberta.

O marco experimental 0.20.0 acrescenta Receive Maximum e Maximum Packet Size
do assinante MQTT 5, inclusive entrega retida/offline e replay após reinício.
Veja a [nota de release](docs/releases/0.20.0.md). O documento de estado
permanece v8; a fase 6C ainda inclui Topic Alias e metadados de publicação.

O marco experimental 0.19.0 acrescenta Message Expiry, Session Expiry no
DISCONNECT e Will Delay MQTT 5. O documento durável passa a v8: faça backup
privado offline antes da atualização, pois 0.18.0 não reabre v7/v8. Consulte
a [nota de release](docs/releases/0.19.0.md) e o
[estado de conformidade](docs/conformance/mqtt5-status.md).

O marco experimental 0.18.0 acrescenta Clean Start e Session Expiry
zero, finita ou infinita ao subconjunto MQTT 5. O estado durável passa a v6;
faça backup offline antes de atualizar e leia a
[nota de release](docs/releases/0.18.0.md) para rollback.

O marco experimental 0.17.0 amplia o subconjunto MQTT 5 para QoS2,
UNSUBSCRIBE, motivos ACL e propriedades informativas de CONNECT. Consulte
[estado de conformidade](docs/conformance/mqtt5-status.md) e
[nota de release](docs/releases/0.17.0.md). As fases 6A–6D ainda estão abertas.

O marco experimental 0.15.0 conclui a fase 5 no recorte local Linux/WSL:
canal administrativo autenticado, política dinâmica aplicada online, auditoria
rotacionável, diagnóstico e métricas. Veja o [aceite](docs/phase5-acceptance.md)
e o [contrato do canal](docs/admin-channel.md). O client independente 0.13.0
inclui os complementos de publicação/assinatura dessa fase.

O marco experimental 0.14.0 acrescenta rotação TLS por SIGUSR1 (P100/B11) e
usuários/ACL estáticos por endpoint mTLS (P101/B09), preservando um roteador,
estado, limite e geração TLS comuns. Consulte [configuração](docs/architecture/configuration.md)
e [transporte seguro](docs/security/secure-transport.md). A campanha física
ESP32 E02 passou na COM4; veja o [aceite da fase 4](docs/phase4-acceptance.md).

O marco 0.13.1 acrescentou o modo `tls-password` (P97/B10) e corrigiu o
default da imagem Docker (P99). A tag de código 0.13.0 ficou sem distribuição.

O marco experimental 0.12.0 acrescenta até três endpoints mTLS adicionais
configurados por `broker.additional_binds` no TOML v1. Eles compartilham a
mesma política, roteador, estado e limite global de conexões; alterações exigem
restart. Veja [configuração](docs/architecture/configuration.md) e o
[registro P96](prompts/registros/P96-endpoints-mtls.md). As políticas por
endpoint e a rotação TLS foram implementadas no marco 0.14.0.

P97 acrescenta `tls-password` para conexões TLS com usuário/senha e ACL, sem
certificado de cliente. É um modo explícito de listener único com estado próprio;
o mTLS permanece padrão. Veja [configuração](docs/architecture/configuration.md).

Marco experimental0.11.6 de robustez: [P89](prompts/broker/89-fechamento-fase3.md),
[fuzz limitado](docs/fuzzing.md), [campanha de recuperação](docs/phase3-campaign.md)
e [CONNACK normativo P93](prompts/broker/93-contrato-connect.md).
O [aceite da fase3](docs/phase3-acceptance.md) registra B06/B07/B08/C07 aceitos
no recorte finito, incluindo encerramento TLS P95 e campanhas finais.
Publicação registrada separadamente em P92;
client0.9.0 e admin independente0.1.0 têm ciclos próprios.
O [planejamento dos três sistemas](../xmqr-admin/docs/planejamento-tres-sistemas.md)
inclui a futura administração de usuários, grupos, papéis e permissões.
MQTT 5 possui publicação, assinatura e cancelamento com sessão limpa.
P122/C63 ampliam publicação e assinatura para QoS0/1/2 na árvore atual;
P123/C64 acrescentam propriedades informativas no CONNECT. Propriedades de
publicação e sessões persistentes seguem pendentes. Veja o
[estado MQTT 5](docs/conformance/mqtt5-status.md).

Veja a [baseline de RAM, CPU e latência P62](docs/performance-baseline.md),
com parâmetros, três repetições, resultados e limites da medição Ubuntu/WSL.

O curso **Da lógica ao Broker e Clientes MQTT utilizando Rust** fica no arquivo
local `../docs/code-guide.html`, na pasta compartilhada `rapidez-broker-client/docs`:
digitação guiada para escrever cada trecho compreendendo lógica, palavras e
símbolos, com checkpoints e exercícios de previsão do resultado. As primeiras
aulas ensinam entrada, impressão, variável e decisão; capítulos avançados
mantêm roteiro e fontes de referência, ainda não aulas humanas de cada linha.
Sidebar e texto têm abertura/fechamento sincronizados, com âncoras de tópicos
e subtópicos. Inclui orientação para usar IA como tutor durante a digitação.
O guia também inclui instalação Rust no Ubuntu/WSL, primeiros projetos Cargo, exemplos TCP com cada
linha explicada, sintaxe/caracteres, comandos, dependências/features e etapas
para acrescentar MQTT, persistência, segurança, operação e distribuição.
Inclui entregas/evidências e fontes atuais numeradas dos dois projetos.
Notas assistidas de instrução/estrutura não substituem análise semântica humana.
Exercícios iniciais são TCP de estudo; ainda não são um broker MQTT completo.

Para regenerar, use Python 3.11+ na raiz do broker, com `xmqr-client` ao lado:

```sh
python3 scripts/build_code_guide.py
```

Os capítulos humanos estão em `scripts/guide_tutorial.py`; novos recursos
exigem revisão do texto, além de regenerar a fotografia das fontes.
O HTML compartilhado está fora da raiz Git deste broker. Os capítulos e o
gerador são versionados aqui; execute o gerador para produzir o curso local.
Na sidebar, a seta de cada tópico e o painel principal abrem/fecham juntos.

### Material do curso para Udemy — P70

Seções e aulas organizadas no HTML local; programação inicial condensada em
duas aulas com checkpoints detalhados. Bibliotecas têm problema resolvido,
funcionamento, termos e limites explicados antes do uso.
O currículo local está em `../docs/curso-udemy/curriculo.json`.

Para gerar os ZIPs cumulativos de prompts e depois atualizar seus links:

```sh
python3 scripts/build_prompt_packages.py
python3 scripts/build_code_guide.py
```

Pacotes em `../docs/curso-udemy/pacotes/`, com índice HTML/JSON e SHA-256.
Cada ZIP inclui contrato, evidências, diff, snapshot acumulado quando há
histórico comprovável e fonte original separada da cópia comentada de leitura.
P00/P01 e outros planos não recebem código inventado; lacunas e marcos que
agrupam tarefas são identificados. Os números dos prompts não são ordem Git.
Material não publicado na Udemy; vídeos e cadastro da plataforma são separados.

### Série nova e cumulativa — Rust nativo Windows

Fonte em `curso/`: P00 define contexto; `projeto-inicial/` implementa o primeiro
recorte P03; `etapas/P04/` acrescenta servidor TCP e `etapas/P05/` client TCP.
Cada pasta contém todos os arquivos da etapa, com comentários de origem e uso.
Não são reconstruções comprovadas dos snapshots antigos; são implementações
didáticas novas. P04/P05 são eco TCP, ainda sem protocolo MQTT.

```powershell
cargo run --locked --offline --manifest-path .\curso\etapas\P05\broker\Cargo.toml
# Em outra janela PowerShell, dentro deste mesmo repositório:
cargo run --locked --offline --manifest-path .\curso\etapas\P05\client\Cargo.toml
```

Índice local em `../docs/curso-udemy/serie-didatica/index.html`, com ZIP por etapa,
código comentado, hashes e diffs. Gerar com `scripts/build_evolution_projects.py`
e `scripts/build_initial_project.py` usando Python3.11+. Os programas Rust
extraídos usam somente sua toolchain, sem Python/WSL/Docker para execução.

Broker MQTT3.1.1 experimental em Rust2024/Tokio, licença MIT. Pacote mqtt-broker;
binários mqtt-broker e mqtt-admin. O client é o projeto independente ../xmqr-client.
O terceiro projeto [XMQR Admin](https://github.com/licodevone/xmqr-admin)
fornece `xmqr-admin`0.4.0 independente, com CLI online e painel web local
autenticado de leitura. Não remove o `mqtt-admin` legado. [Registro P88](prompts/registros/P88-admin.md).
Não há declaração de conformidade completa ou prontidão para produção.

## Versões

Marco atual: [broker/admin legado v0.15.0](https://github.com/licodevone/xmqr/releases/tag/v0.15.0)
e [client independente v0.13.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.13.0),
prereleases experimentais da [fase 5 aceita](docs/phase5-acceptance.md).
Pacotes Ubuntu 26.04 amd64, imagens numeradas, manifests e SHA-256 estão nos
assets de cada release. Admin independente mantém seu versionamento próprio.

P80 corrige shutdownTLS do cliente não leitor; [fase2 por componente](docs/phase2-acceptance.md)
tem software e ESP32 físico validados após P85/C44: fase2 concluída no escopo
definido, sem conformidade integral ou produção inferida.

Marco anterior: **broker/admin legado 0.11.6**, fase3 aceita no
[recorte experimental](docs/phase3-acceptance.md).
[Prerelease](https://github.com/licodevone/xmqr/releases/tag/v0.11.6)
com .deb Ubuntu26amd64, exports de imagens Docker, checksums e evidências.
Client0.9.0 publicado independentemente; versões anteriores preservadas.
Admin independente0.1.0: [release experimental](https://github.com/licodevone/xmqr-admin/releases/tag/v0.1.0)
com pacote `xmqr-admin` e imagem `lepinheiro100/xmqr-admin-ui:0.1.0`, sem
conflito com o utilitário legado0.11.6. Painel não controla ACL/sessões ao vivo.
Consulta de versão do
admin, imagem admin separada e contexto Docker seguro. O [plano detalhado de
paridade com Mosquitto](docs/plano-paridade-mosquitto.md) está concluído como
planejamento; fases pendentes continuam sem implementação nesta entrega.

Veja o [plano de evolução do broker e dos clients](docs/evolution-plan.md),
com lacunas frente ao Mosquitto, ordem de implementação e cronograma estimado.

| Versão | Marco |
| --- | --- |
| 0.3 | laboratório aberto restrito a loopback |
| 0.4 | senha, ACL e administração de usuários |
| 0.5 | filtros +/#, regra $ e interoperabilidade |
| 0.6 | Last Will durável e revisão de retained |
| 0.7 | health/readiness/métricas HTTP opcionais loopback |
| 0.8 | segurança dinâmica por bundle e SIGHUP |
| 0.9 | backup/verify/restore offline e Docker; tag v0.9.0 publicada |
| 0.10 | parada coordenada, systemd e deb Ubuntu26.04 amd64 |
| 0.11 | TOML, quotas e pacote completo; fase1 aceita em Ubuntu26 |

Veja [CHANGELOG](CHANGELOG.md), [versionamento](VERSIONING.md) e releases no GitHub.
Tags antigas são imutáveis; releases0.x são experimentais. Histórico de execução
em prompts/registros descreve o resultado de cada marco, não o estado atual.

## Instalação Ubuntu / WSL

O pacote publicado é experimental e destinado ao Ubuntu 26.04 **amd64**.
Ainda não há repositório APT próprio: baixe o `.deb` e instale-o com o APT.

1. No Windows, abra sua distribuição pelo PowerShell (confira o nome com
   `wsl --list --verbose`):

```powershell
wsl -d Ubuntu-26.04
```

2. Execute os próximos comandos **no terminal do Ubuntu**. Confirme a versão
   e a arquitetura; este pacote requer Ubuntu 26.04 e `amd64`:

```bash
cat /etc/os-release
dpkg --print-architecture
sudo apt update
sudo apt install -y wget ca-certificates
mkdir -p ~/xmqr-pacotes
cd ~/xmqr-pacotes
```

3. Baixe o pacote e seu checksum da release publicada:

```bash
wget -O xmqr-broker_0.11.6-1_amd64.deb https://github.com/licodevone/xmqr/releases/download/v0.11.6/xmqr-broker_0.11.6-1_amd64.deb
wget -O xmqr-broker_0.11.6-1_amd64.deb.sha256 https://github.com/licodevone/xmqr/releases/download/v0.11.6/xmqr-broker_0.11.6-1_amd64.deb.sha256
sha256sum -c xmqr-broker_0.11.6-1_amd64.deb.sha256
```

Prossiga somente se a verificação mostrar `OK`.

4. Instale e confirme o pacote e a conta de serviço:

```bash
sudo apt install ./xmqr-broker_0.11.6-1_amd64.deb
dpkg-query -W -f='${Status}\n' xmqr-broker
id xmqr
```

O resultado esperado é `install ok installed`. A instalação cria o usuário e
grupo `xmqr`; não é necessário criá-los manualmente. Se `dpkg-query` informar
que não encontrou o pacote, a instalação ainda não foi concluída.

5. Configure os certificados, credenciais e permissões conforme o
   [guia Ubuntu e systemd](docs/ubuntu-systemd.md),
   [transporte seguro](docs/security/secure-transport.md) e
   [administração de usuários](docs/administracao-usuarios.md).
   Revise `/etc/xmqr/broker.env` e instale os arquivos referenciados por ele:
   `server.crt`, `server.key`, `clients-ca.crt` e `security.toml` em `/etc/xmqr`.
   A chave privada e o bundle de segurança devem pertencer a `xmqr:xmqr`, com
   permissão `0600`. Não publique chaves privadas ou senhas no GitHub.

6. Após configurar TLS, usuários e ACL, habilite e inicie o serviço:

```bash
sudo systemctl enable --now xmqr-broker.service
systemctl status xmqr-broker.service
journalctl -u xmqr-broker.service -f
```

Use `Ctrl+C` para sair do acompanhamento dos logs. O pacote não inicia o broker
automaticamente. No WSL, o systemd deve estar habilitado; veja o guia acima.
O serviço habilitado inicia quando a distribuição Ubuntu é iniciada.

Para atualizar, baixe a nova versão, confira o checksum e repita a instalação
com `sudo apt install ./ARQUIVO.deb`. A atualização preserva configuração e
dados, mas para o serviço; revise a configuração e inicie-o novamente com
`sudo systemctl start xmqr-broker.service`.

## Compatibilidade Ubuntu

| Ambiente amd64 | Evidência atual |
| --- | --- |
| Ubuntu 26.04 / WSL2 | Pacotes instalados e testes de integração e systemd com TLS/mTLS aprovados. Alvo atual dos pacotes publicados. |
| Ubuntu 24.04 / WSL2 | Os mesmos binários executaram testes de integração; instalação do `.deb` e units nessa versão ainda não validadas. |
| Outras versões Ubuntu, outras distribuições ou arm64 | Não validadas. Não há pacote arm64 publicado nesta etapa. |

Os pacotes atuais requerem `libc6 >= 2.38`, `libgcc-s1 >= 4.2`, `adduser` e
`init-system-helpers`. No Ubuntu 24.04 testado, a glibc é 2.39 e os binários
conseguem executar. Isso não equivale a suporte completo nessa distribuição:
o teste de sessão após reinício recebeu uma mensagem QoS1 repetida na primeira
execução e passou na repetição; a causa ainda não foi confirmada. O gerador de
pacotes permanece restrito ao Ubuntu 26.04 amd64. Não force dependências nem
substitua a glibc do sistema para instalar um pacote.

## Controlar o broker com systemctl

Execute os comandos abaixo no terminal Ubuntu/WSL, após a instalação e a
configuração de certificados, usuários e ACLs. `sudo` autoriza alterações no
serviço; as consultas geralmente não precisam dele.

| Objetivo | Comando | Efeito |
| --- | --- | --- |
| Iniciar | `sudo systemctl start xmqr-broker.service` | Inicia agora, sem alterar o início automático. |
| Consultar status | `systemctl status xmqr-broker.service` | Mostra estado, processo e registros recentes. |
| Parar | `sudo systemctl stop xmqr-broker.service` | Solicita encerramento coordenado do broker. |
| Reiniciar | `sudo systemctl restart xmqr-broker.service` | Para e inicia novamente; desconecta os clientes. |
| Habilitar início automático | `sudo systemctl enable xmqr-broker.service` | Habilita para a próxima inicialização, sem iniciar agora. |
| Habilitar e iniciar agora | `sudo systemctl enable --now xmqr-broker.service` | Combina início automático e início imediato. |
| Desabilitar início automático | `sudo systemctl disable xmqr-broker.service` | Remove o início automático, sem parar o processo atual. |
| Desabilitar e parar | `sudo systemctl disable --now xmqr-broker.service` | Remove o início automático e para agora. |
| Consultar atividade | `systemctl is-active xmqr-broker.service` | Exibe, por exemplo, `active`, `inactive` ou `failed`. |
| Consultar início automático | `systemctl is-enabled xmqr-broker.service` | Exibe, por exemplo, `enabled` ou `disabled`. |

`active (running)` indica que o processo está em execução; confirme também uma
conexão MQTT para validar certificados, autenticação e permissões. `inactive
(dead)` significa que o serviço está parado; `failed` indica uma falha.
`Unit ... could not be found` indica que a unit não está disponível: confirme
a instalação com `dpkg-query -W xmqr-broker`.

### Tabela comparativa de comandos

Execute no Ubuntu/WSL. `device` é o nome da instância do client de assinatura;
substitua-o pelo nome configurado em `/etc/xmqr-client/NOME.conf`.

| Ação | Broker | Client de assinatura |
| --- | --- | --- |
| Iniciar | `sudo systemctl start xmqr-broker.service` | `sudo systemctl start xmqr-client-sub@device.service` |
| Ver status | `systemctl status xmqr-broker.service` | `systemctl status xmqr-client-sub@device.service` |
| Parar | `sudo systemctl stop xmqr-broker.service` | `sudo systemctl stop xmqr-client-sub@device.service` |
| Reiniciar | `sudo systemctl restart xmqr-broker.service` | `sudo systemctl restart xmqr-client-sub@device.service` |
| Iniciar agora e automaticamente | `sudo systemctl enable --now xmqr-broker.service` | `sudo systemctl enable --now xmqr-client-sub@device.service` |
| Parar e desativar início automático | `sudo systemctl disable --now xmqr-broker.service` | `sudo systemctl disable --now xmqr-client-sub@device.service` |
| Verificar se está ativo | `systemctl is-active xmqr-broker.service` | `systemctl is-active xmqr-client-sub@device.service` |
| Verificar início automático | `systemctl is-enabled xmqr-broker.service` | `systemctl is-enabled xmqr-client-sub@device.service` |

### Acompanhar e consultar os logs

```bash
# Acompanhar novos registros em tempo real
journalctl -u xmqr-broker.service -f

# Consultar as últimas 50 linhas e sair
journalctl -u xmqr-broker.service -n 50 --no-pager

# Consultar os registros desta inicialização do Ubuntu
journalctl -u xmqr-broker.service -b --no-pager

# Consultar apenas registros dos últimos 10 minutos
journalctl -u xmqr-broker.service --since "10 minutes ago" --no-pager
```

`journalctl` consulta o journal do systemd; `-u` filtra a unit do broker e `-f`
mantém o acompanhamento aberto. Não inicia nem para o serviço. Pressione
**Ctrl+C** para sair do acompanhamento. Na tela paginada de `systemctl status`,
pressione **q** para sair. Para status sem paginador, use
`systemctl status xmqr-broker.service --no-pager`. Se não tiver acesso aos logs,
execute a consulta com `sudo`.

### Recarregar segurança e aplicar configurações

```bash
# Recarregar o bundle de usuários e ACLs
sudo systemctl reload xmqr-broker.service
```

O reload envia SIGHUP e recarrega o bundle de segurança dinâmica configurado.
Um reload válido encerra as conexões dinâmicas para exigir nova autenticação.
Não aplica alterações em `/etc/xmqr/broker.env` ou nos certificados: para essas
alterações, use `sudo systemctl restart xmqr-broker.service`.

Se editar uma unit ou seu override, execute `sudo systemctl daemon-reload`
antes de reiniciar. Esse comando recarrega as definições do systemd; não
recarrega sozinho a configuração MQTT nem reinicia processos.

### Diagnóstico e uso no WSL

Confira primeiro o status e os logs. Após corrigir um erro que atingiu o limite
de tentativas de início, limpe o estado de falha e tente iniciar:

```bash
sudo systemctl reset-failed xmqr-broker.service
sudo systemctl start xmqr-broker.service
```

`reset-failed` não corrige certificados, credenciais ou arquivos ausentes. O
broker tem reinício automático em falhas, limitado a cinco inícios por 120
segundos; uma parada solicitada por `stop` não provoca reinício automático.

No WSL, confira o processo principal com `ps -p 1 -o comm=`: deve ser `systemd`.
Se não for, siga o [guia Ubuntu/WSL](docs/ubuntu-systemd.md). Uma unit habilitada
inicia quando a distribuição Ubuntu é iniciada. Os comandos controlam os
serviços dessa distribuição Linux. Para iniciar o broker e depois seu client
de assinatura, veja também o [README do client](../xmqr-client/README.md).

## Recursos e limites

QoS0/1/2, retained, sessões persistentes, SUBSCRIBE/UNSUBSCRIBE, filtros +/#,
Last Will durável, TLS/mTLS, senha Argon2id e ACL deny-by-default.
Persistência por WAL/snapshot e ator dedicado, commit durável antes de ACKs
pertinentes. SIGTERM/SIGINT coordenam listener, Wills e shutdown do writer.
MQTT 5 oferece sessões, propriedades e opções de assinatura em recortes
experimentais; o aceite global das fases 6A–6D segue aberto. WS local está
na 0.39.0 e WSS mTLS local na 0.40.0; bridge ainda não existe.
Consulte o [plano de evolução](docs/evolution-plan.md) para limites e evidências.

Limites:64 conexões/sessões,256 assinaturas por sessão,64 mensagens offline,
32 inflight,1024 bytes UTF-8 por tópico/filtro,4096 bytes por payload e64KiB
por pacote. São quotas de projeto, não benchmarks de capacidade.

secure-mtls é o padrão, com certificado+senha+ACL. open-lab/password-lab/acl-lab
são apenas loopback e usam estados separados. Não exponha os laboratórios à rede.
Backup/administração durável requerem Linux/WSL. Monitoramento é opcional e
loopback; active no systemd não comprova readiness MQTT.

## Compilar e laboratório

Rust1.88 declarado (toolchain exato ainda não validado); build atual Rust1.99.

```sh
cargo build --locked --bins
cargo build --manifest-path ../xmqr-client/Cargo.toml --locked --bin mqtt-client
```

[Laboratório progressivo](docs/laboratorio-mqtt-aberto.md) contém o roteiro de
publicação/assinatura. [Docker](docs/docker.md) explica imagem e volumes;
[cliente independente](../xmqr-client/README.md) tem as opções atuais.

## Validação e documentação

```sh
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
python3 scripts/license_inventory.py --check
cargo build --locked --bins
python3 scripts/verify_shutdown.py --broker target/debug/mqtt-broker
```

Interoperabilidade externa: scripts/verify_interop.py requer clientes Mosquitto;
seu CI executa open-lab. Isso não prova TLS/mTLS externo nem conformidade total.

- [Matriz MQTT](docs/conformance/mqtt311-status.md)
- [Persistência e backup](docs/architecture/persistence.md)
- [Segurança dinâmica](docs/security/dynamic-security.md)
- [Transporte seguro](docs/security/secure-transport.md)
- [Administração](docs/administracao-usuarios.md)
- [Monitoramento](docs/monitoring.md)
- [Roadmap](docs/ROADMAP.md)
- [Contribuição](CONTRIBUTING.md)
- [Segurança](SECURITY.md)
- [Licenças de terceiros](docs/third-party-licenses.md)

Preserve MIT e atribuições de terceiros ao redistribuir. Nunca versionar secrets
ou estado MQTT. Registro desta etapa: prompts/registros/P47-systemd-ubuntu.md.

## Publicação verificada

Prerelease da fase1: [v0.11.0](https://github.com/licodevone/xmqr/releases/tag/v0.11.0),
com deb Ubuntu26 amd64 e checksum. Aceite local completo em
[registro P61](prompts/registros/P61-aceite-final-fase1.md); não confundir com CI histórica0.10.

## Configuração TOML (código após P52)

O pacote0.11.0 aceita MQTT_CONFIG apontando para um TOML version=1.
A instalação preserva broker.env e não ativa o TOML automaticamente.
Em [limits], max_connections permite definir de1 a64 conexões TCP simultâneas;
MQTT_MAX_CONNECTIONS prevalece sobre o arquivo. O padrão continua64.
Veja [campos e exemplo](docs/architecture/configuration.md) e
[arquivo de exemplo](packaging/broker.toml.example). A precedência é defaults,
TOML e variáveis MQTT_* explícitas, nessa ordem. Caminhos relativos no TOML
partem da pasta do arquivo. Reinicie o broker após alterações. O exemplo usa
bundle de segurança existente; ele não cria certificados nem credenciais.


### Quotas P55 — aceitas na fase1

Quotas lógicas de sessões, retained, assinaturas, offline e inflight estão
implementadas localmente, com defaults/tetos anteriores e rejeição de reduções
incompatíveis. Aceite Ubuntu26 concluído emP61 e incluído no pacote0.11.0.
Veja [contrato de configuração](docs/architecture/configuration.md) e
[registro P55](prompts/registros/P55-quotas-estado.md).

P55 rev3: saturação ao publicar Last Will torna o ator indisponível e encerra
conexões, preservando a obrigação durável para restart com quotas suficientes.
Consulte [configuração](docs/architecture/configuration.md) e
[registro P55](prompts/registros/P55-quotas-estado.md) e
[aceite final P61](prompts/registros/P61-aceite-final-fase1.md).


P58 alinha o teto do broker ao client:64KiB (65536 bytes) do pacote MQTT
completo, incluindo primeiro byte e Remaining Length. Payload PUBLISH/Will
continua4096 bytes e tópico/filtro1024 UTF-8. Excesso declarado é recusado
antes do corpo; quotas e formato durável preservados. Evidência e pendências
em [registro P58](prompts/registros/P58-pacote-completo.md).

## Docker — distribuição P63/C40

Imagens lepinheiro100/xmqr-broker:0.11.6 e lepinheiro100/xmqr-admin:0.11.6 para Linux/amd64,
com tar.gz/SHA-256/proveniência na prerelease. O pacote do broker também inclui
.debUbuntu26amd64. [Build/load, configuração e execução](docs/docker.md).
Sem chaves/estado na imagem; usuário10001, mTLS e volumes externos.

## Consultar a versão — P64

```sh
mqtt-broker --version
mqtt-broker -V
docker run --rm lepinheiro100/xmqr-broker:0.11.6 --version
mqtt-admin --version
docker run --rm lepinheiro100/xmqr-admin:0.11.6 --version
```

Saída: `mqtt-broker 0.11.6` ou `mqtt-admin 0.11.6`, exit0. Funciona sem configuração, certificados,
credenciais ou estado: os argumentos são tratados antes do runtimeTokio/logs.
Sem argumentos, inicia normalmente conforme configuração. Argumentos não
suportados/combinados retornamexit2 sem reproduzir seus valores. Não há --help
nesta fatia. A distribuição P78/C42 inclui publicação versionada no Docker Hub
lepinheiro100, mantendo tags antigas/latest. Confira os digests e o manifesto
dos artefatos na prerelease antes de atualizar.
