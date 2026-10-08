# P44 - segurança dinâmica, proposta 0.8.0

Versão do prompt 1.0, 2026-10-08. Estado: preparado, NÃO EXECUTADO.
Autorização: evoluir incrementalmente broker e cliente, inspirado no Mosquitto.
Este prompt trata somente o broker. Implementação começa depois da publicação
ou resolução explícita do checkpoint P43/0.7 pelo mantenedor. Não alterar Cargo
para 0.8, credenciais reais, clientes ou qualquer serviço nesta preparação.

## Estado e referência

Base HEAD bc4cc55, working tree com P43/C25 não commitados. Marco 0.7 local
validado em WSL Ubuntu-26.04/Rust1.99 sobre /mnt/d/projects/my-project/xmqr:
72 testes, fmt/Clippy/inventário/build, 6 integrações HTTP/MQTT e 9 Will PASS.
MIT e documento MQTTv2/WALv1 preservados; não há tag0.7 criada pelo agente.
AccessPolicy/AuthPolicy são snapshots imutáveis compartilhados por Arc,
selecionados no startup; roteador revalida ACL no fan-out/restore. Autenticação
Argon2 usa quatro slots. MQTT3.1.1 é o contrato atual.

Referência primária: https://mosquitto.org/documentation/dynamic-security/
Mosquitto permite atualizar segurança em execução, com clientes, grupos e
papéis. Inspiração funcional, sem copiar código, formato, prioridades ou API
de tópicos administrativos. XMQR preservará deny-by-default também na entrega.

## Objetivo e fatias antes de publicar 0.8

Atualizar usuários/permissões sem reiniciar, com publicação atômica de uma
geração de política e revogação verificável em conexões e estado persistente.
P44a: reload de usuários/ACL e fronteira de gerações. P44b: grupos/papéis
opcionais, depois de P44a passar; completar ambos antes de anunciar 0.8 pronta.
Sem bridge, WebSocket, MQTT5 ou quotas MQTT novas nesta fatia.

## Configuração e controle local propostos

Adicionar modo opt-in MQTT_SECURITY_BUNDLE, um único TOML versionado contendo
usuários (hash Argon2, fingerprint), concessões, grupos e papéis. Ler um único
arquivo evita combinar users/ACL de gerações diferentes. Manter caminhos
legados de startup compatíveis; bundle e arquivos legados são mutuamente
exclusivos. Open-lab segue anônimo/loopback e rejeita configuração de segurança.
TLS/CA/CRL e modos de transporte não serão recarregados nesta etapa.

Trigger inicial local Unix SIGHUP, com um reload em andamento e coalescimento
limitado. Sem API HTTP/MQTT administrativa ou controle remoto novo. Documentar
o PID/executável correto; testar apenas processos próprios. Mudança de arquivo
não significa política aplicada até confirmação da geração publicada.

O leitor faz I/O/parse/validação fora dos workers Tokio e não modifica arquivos
do usuário. Bundle privado/regular, limite1MiB, sem logar conteúdo ou hashes.
Usar publicação por arquivo temporário+rename+fsync no fluxo administrativo
futuro; não editar credenciais reais nesta tarefa. Reload inválido preserva
integralmente política/estado anteriores; startup inválido falha fechado.

## Semântica de grupos e papéis

Usuário identificado por username; grupos não aninhados, papéis com concessões
publish e subscribe. Permissão efetiva é união de concessões diretas e papéis
diretos/de grupo; ausência de concessão nega. Sem prioridades ou deny explícito
nesta fatia, evitando precedência ambígua. Subscribe mantém filtro literal;
entrega concreta revalida autorização. Não introduzir substituição %u/%c.
Referências inexistentes/duplicatas/ciclos são erros. Propor limites128 grupos,
128 papéis,64 vínculos por usuário e256 concessões por papel, além de quotas
atuais de usuários/regras/arquivo; confirmar essas novas quotas no prompt da
implementação e testar fronteiras. Não ampliar limites MQTT existentes.

## Publicação atômica e revogação

Construir snapshot candidato completo e imutável; compartilhar o mesmo limite
global de quatro hashes entre gerações, sem multiplicar workers por reload.
Conexões autenticadas recebem geração de credencial; autenticação que termina
após troca não pode registrar com decisão antiga. Gate de Register verifica
geração atual. Nenhum lock bloqueante atravessa await/disco/hash.

Serializar troca no ator de roteamento como barreira de comandos. Preparar
estado candidato revalidando subscriptions/offline/inflight/Will, fazer commit
durável e somente então publicar snapshot/geração e confirmar reload. Se falhar
persistência, não anunciar sucesso e aplicar fail-closed existente. Reinício
usa bundle configurado e revalida recuperação; sem política parcial no WAL.

Remover/desabilitar usuário ou trocar hash/fingerprint encerra conexões antigas
e exige novo CONNECT. ACL alterada passa a reger conexões atuais. Remover
assinaturas negadas e impedir entregas enfileiradas obsoletas com geração nas
entregas e rechecagem antes do wire; tratar writer já em andamento com barreira
explícita antes da confirmação do reload. Bytes já enviados não são retratáveis.
Documentar exatamente a linearização, sem prometer revogação retroativa.

Will usa política efetiva na publicação; negar novo privilégio descarta o Will
duravelmente. Alteração de senha que encerra conexão ainda revalida Will pela
ACL atual. Preservar regras de DISCONNECT, takeover e gerações antigas.
QoS2 aceito antes de PUBREC permanece responsabilidade do broker; não apagar
estado aceito arbitrariamente por revogação do publicador. Entrega/replay usam
ACL atual do destinatário. Especificar recuperação de QoS2 sem credencial ativa
antes de codificar, preservar handshake/identificadores e quotas existentes.

## Arquivos e validação

auth/{mod,novo bundle}, main, mqtt/{mod,router,store}, testes, config.example
sem secrets, docs/security, matriz, registro e métricas de reload com labels
fixos. Sem mudança de formato MQTT durável se não indispensável; se necessária,
preparar revisão de prompt/migração/backup antes de codificar. Preferir deps atuais.

Aceite: geração troca uma vez; inválido/oversize/referência ruim mantém anterior;
nenhum bypass entre CONNECT antigo e Register; revogação durante publish,
SUBSCRIBE, replay, retained, offline, inflight, PUBREC/PUBREL e Will; takeover;
grupo removido/usuário desabilitado/troca de senha; fila reload saturada;
falha commit/restart e shutdown; quatro slots Argon2 continuam globais;
nenhum segredo em erro/label. Fixtures independentes e credenciais temporárias.
Consultar requisitos OASIS antes de alterar semântica de wire.
Fmt/test/Clippy/inventário/build e regressões P43/P42 obrigatórios. Ampliar
negativos secure-mtls/ACL com identidades temporárias; ferramentas ausentes
BLOCKED, sem instalar. Registrar comandos, geração, rollback e limites reais.

## Checkpoint

P44 preparado apenas. Nenhum código 0.8 implementado. Primeiro usuário publica
ou resolve marco0.7; depois executar uma fatia por vez e parar na validação0.8.
Sem commit/push/tag/release automático. Demais recursos ficam no roadmap.

## Revisão 1.1 - implementação autorizada, 2026-10-08

Base confirmada: HEAD/tag local e remota v0.7.0 = 3a3dde7; working tree limpo.
WSL26/Rust1.99 responde. Nova autorização permite executar P44 local; preservar
cliente paralelo C28. Implementar0.8 somente no broker, sem publicação.

Controle inicial SIGHUP local Unix e bundle privado com schema1; secure-mtls e
acl-lab opt-in, rejeitar open-lab/password-lab e combinação com users/ACL legados.
Grupos/papéis com união de grants exatos publish e filtros literais subscribe.
Reload válido faz commit de reconciliação antes de troca; inválido mantém anterior.
Para revogação coerente nesta fatia, TODAS as conexões dinâmicas são encerradas
após reload válido e exigem reautenticação; permissões novas não exigem restart
broker. Documentar interrupção de conexões. Will permitido publicado e Will
revogado descartado uma vez na transição durável; limpar clean sessions.
Preservar inboundQoS2 aceito de sessões persistentes mesmo com principal removido,
sem capacidade de novo CONNECT até reativação; restaurar esse estado sob bundle
sem permitir auth/grants ausentes. Não apagar ownership transferido antes PUBREC.
Decisões novas após publicação usam política atual; frames já em escrita são
irretratáveis e explicitamente anteriores à barreira. Epoch no CONNECT/Register
impede autenticação concorrente obsoleta. Quatro slots Argon2 globais.
Audit apenas sucesso/falha/geração fixa, sem usernames/payload/hash/paths secretos.
Gates/parser/negativos/reload/Will/retained/offline/QoS2 e regressões P43 obrigatórios.


## Checkpoint final — 2026-10-08

P44 implementado e validado localmente. Gates e resultados completos estão em
[registro P44](../registros/P44-0.8.0.md). Interface administrativa: SIGHUP local
Linux/WSL, sem API remota; reload válido encerra todas as conexões dinâmicas.
Validação existente de identidade/certificado secure-mtls preservada.
Cliente paralelo preservado. Sem commit, push, tag ou release; parar neste marco.
