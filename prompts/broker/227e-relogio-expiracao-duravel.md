# P227E v2.8 — relógio lógico e expiração durável sem renovar TTL

Preparado em18 de outubro de2026 antes de testes/fontes desta correção.
Complementa P227, sem reabrir as correções aceitas P227C/P227D. Base de leitura:
broker0.42.0, documento v15; conferir HEAD e dirty antes de cada commit.
Coordenação autoriza clock/router/store/mod.rs e testes próprios. Codec é de
outra frente, Cargo/versão/admin/release pertencem ao coordenador.

## Lacuna original, não extensão nova

[P130 rev1](130-message-expiry-mqtt5.md) exige: persistir instante absoluto e
intervalo original para o cálculo encaminhado. StoredMessage atualmente só
guarda expiry_at_unix_ms; remaining_message_expiry subtrai SystemTime::now.
Recuo UTC após recebimento pode aumentar TTL, inclusive acima do original.
O teste existente cobre pré-epoch/overflow, não regressão com tempo live.

[OASIS MQTT5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
§3.3.2.3.3/MQTT-3.3.2-5/-6 requer descartar cópia cujo encaminhamento ainda
não começou e reduzir o intervalo encaminhado pelo tempo aguardado. Não
transformar isso em promessa de NTP/energia ou deadline físico exato. O
comentário não normativo §3.1.2.11.2 admite relógio parado durante downtime;
não autoriza aumentar TTL durante o processo. Somente limitar ao intervalo
original é insuficiente depois de parte do tempo live já ter decorrido.

## Desenho mínimo e compatibilidade

1. Relógio de expiração único, compartilhado pelo router e handler, com
   Instant para progresso do processo e piso UTC lógico que nunca recua.
   Salto UTC adiante pode avançar esse piso; recuo não o reduz. Amostragem
   barata com atômicos, sem locks bloqueantes/disco no cálculo. Pré-epoch,
   overflow e entrada monotônica inválida falham fechado. Fonte sintética
   de teste por instância, sem flags públicas nem mudança do relógio host.
2. Guardar watermark lógico no agregado e intervalo original opcional em
   StoredMessage. Toda transição candidata usa o mesmo relógio e grava o
   watermark antes da barreira WAL. Calcular deadline com esse relógio;
   preservar intervalo original em retained/offline/QoS e na publicação do
   Will, sem alterar handshake já iniciado ou ownership QoS1/2.
3. Documento v16: os novos campos em tipos deny_unknown_fields não podem
   ser disfarçados de v15 compatível. Ler v1–v15, escrever v16; recusar
   futuro/corrupção/quotas sem truncamento. Legacy sem intervalo original
   permanece None: não inventar histórico. Na primeira recuperação legada,
   usar UTC disponível; proteção de watermark começa com o primeiro commit
   v16. Não reconstruir tempo/perda anterior à migração. Restore v16 parte
   do máximo entre UTC e watermark e volta a progredir por Instant.
4. Admin independente precisa novo pin/core e prova v16 antes de publicar;
   coordenador fará isso após checkpoint funcional validado. Rollback a
   broker/admin v15 exige backup privado anterior, não converter estado
   ativo. Sem edição de Cargo/admin nesta fatia.

## Fronteira de commit, encode e início do encaminhamento

Para uma cópia com expiry cujo encaminhamento ainda não começou, pedir ao
ator uma permissão de envio: instante lógico T, deadline e R segundos inteiros
restantes (arredondamento para cima), limitado ao original quando conhecido.
O ator persiste watermark>=T antes de liberar essa permissão. Falha WAL não
autoriza encode/envio nem se mascara como mensagem expirada.

Depois da barreira, imediatamente antes de encode/iniciar write, conferir o
mesmo relógio. Só emitir o R certificado enquanto o restante pertence à mesma
faixa inteira R. Se caiu, obter permissão nova com watermark novo; se venceu,
não iniciar o envio e concluir descarte durável pelo caminho existente. Não
emitir TTL menor não coberto por checkpoint: após restore o watermark dessa
faixa garante TTL<=último R emitido, mesmo com UTC recuado. Não reservar
watermark futuro nem encurtar artificialmente validade para esconder a janela.

Refresh é limitado por deadline monotônico explícito de3s e no máximo4
tentativas, sem loop ilimitado se cada fsync consumir uma faixa. Esgotamento
encerra/retorna erro preservando obrigação durável; erro de persistência
propaga falha, não ACK/sucesso. Encode e início do write não têm awaits entre
a checagem final e a chamada de escrita. O instante considerado é o início
do encaminhamento pelo software, não a confirmação física do primeiro byte.
Após iniciado o handshake/envio, não cancelar QoS por expiração posterior.
Quotas, canais e deadlines existentes permanecem, sem nova fila ilimitada.

## RED → GREEN e aceite

Commitar este prompt antes das fontes. Preparar RED determinístico para
relógio live recuado e tempo decorrido, retomada com watermark e TTL já
encaminhado. Não ajustar relógio global/WSL, instalar ou tocar serviços.
Revisar prompt após qualquer falha inesperada antes de corrigir fonte.

Testes: intervalo10, avanço3s→7, recuoUTC com avanço monotônico→6 e depois
expira; salto adiante não ressuscita em recuo; pré-epoch/overflow; original0
e U32_MAX. Live/retained/offline e recuperação v16 não aumentam prazo. Tempo
avança durante commit falso: mesma faixa libera, cruzamento exige checkpoint
novo, limite falha sem entregar/perder ownership. WAL injetado recusa envio.
Migração sintética v1–v15 preserva dados e marca honestamente sua origem;
fixture real v15→v16 será coordenada com binários congelados. Legado sem
original permanece ausente. Testar novo formato, recusa por antigos e pin
admin antes da distribuição, não declarar isso só por existir parser.

Executar fmt dos arquivos próprios e testes dirigidos locked/-j1 em janela
Cargo coordenada; regressões de expiry/session/Will/QoS/flow/migração.
Principal faz gates completos, wire e distribuição após congelar fonte/ELF.
Não alterar codec, CI, Cargo/versão, bridge/C129 alheios, hardware/firewall,
tags/push/release nesta implementação. MIT/terceiros preservados; registrar
PASS/FAIL/BLOCKED e limitações sem promover evidência histórica.

## Revisão v1.1 após RED, antes do fix e dos novos inicializadores

Prompt inicial commitado fc3b40a. Extraído o cálculo existente para módulo
clock com fonte sintética por instância e comportamento inicial UTC-only,
sem watermark/progresso monotônico aplicado ainda. RED unitário real, não
wire nem relógio host: cargo test --locked --lib p227e_ -j1 resultou3FAIL
de asserção/exit1 em0,02s após64s de compilação; live/restore retornaram19
em vez de6 e salto adiante seguido de recuo retornou10 em vez de0.
Dois avisos temporários de campo/construtor ainda não integrados não são
PASS de Clippy. Nenhum dado do operador foi lido ou relógio alterado.

Agora integrar a correção. Coordenador autorizou adicionalmente somente os
inicializadores mecânicos de StoredMessage em codec.rs e fuzz_tests.rs,
com expiry_interval_seconds:None, necessários ao novo campo. Parser,
framing e testes P227D não mudam. Will pendente continua sem intervalo no
StoredMessage até will_publication criar prazo+intervalo no instante certo.

## Revisão v1.2 antes da correção de lint

GREEN10/10 novos; regressões expiry13/13, Will14/14, receive_maximum4/4 e
reads_v3/3 PASS. Clippy --lib -Dwarnings FAIL por quatro diagnósticos:
reload de segurança102linhas, assinatura serde is_zero(&u64), QoS sem crases
em comentário próprio anterior e single_match_else na abertura do clock.
Corrigir apenas essas formas, com exceções estritamente locais justificadas
onde serde/transação exigem o formato. Não suprimir avisos globalmente.
Esclarecer mensagens/registro: checkpoint falho não libera permissão ou ACK;
ownership durável permanece enquanto a sessão existe. Encerrar uma sessão
CleanStart/Expiry0 pode descartá-la legitimamente; não prometer retenção além
da vida normativa da sessão. Limite de bytes do documento1MB permanece;
migração que o exceder falha fechado, sem aumentar quota ou truncar legado.

## Revisão v1.3 antes do marcador de tentativa e testes novos

Revisão independente confirmou clock/permit/barreira e encontrou fronteira
anterior: prepare_delivery persistia AwaitPubAck/Rec antes da fila/write;
todo replay era DUP1 e isento de expiry. Isso não distingue fila nunca
tentada de tentativa incerta após crash. P130 proíbe encaminhar cópia já
expirada cujo envio não começou, mas não permite apagar QoS2 já enviado.

O coordenador aprovou marcador durável Prepared/MayHaveSent em
OutboundInflight, ainda no v16 não publicado. Default legado MayHaveSent,
sem afirmar reconstrução do primeiro write. Cópia nova com expiry começa
Prepared; demais cópias conservam default e comportamento. prepare_expiry
deve validar packet_id/geração/metadata, mudar Prepared para MayHaveSent no
mesmo checkpoint e só então autorizar write. Falha WAL não muda a fase.
Janela checkpoint→primeiro byte permanece intenção incerta, explicitamente
MayHaveSent, não confirmação de byte físico. Timeouts/refresh não apagam
obrigação já possivelmente enviada. Recuperar Prepared fresco como primeira
tentativa DUP0 e descartar Prepared vencido antes de reservar tentativa;
MayHaveSent expirado conserva handshake/DUP1 e não é reclassificado.

Preparar RED antes do fix: crash lógico após commit antes de permit;
restore Prepared expirado/fresco; MayHaveSent expirado como controle;
permit exige transição antes do retorno e WAL negativo conserva Prepared.
Introduzir primeiro somente campo/enum/defaults que preservam a política
anterior, sem anunciar fix. Não alterar quotas ou caminho sem expiry.
Revisor continua read-only sem Cargo paralelo; este owner implementa fontes
e testes. Rever prompt antes de corrigir FAIL inesperado. Encerramento de
P227E depende destes testes e do review; GREEN anterior não fecha essa janela.

## Revisão v1.4 antes de corrigir o launcher dos testes RED

Primeira compilação do RED de intenção falhou E0433 no inicializador mecânico
de fuzz_tests.rs: esse arquivo é incluído no contexto de testes do codec,
logo super::store não existe ali. Isso não é RED de asserção nem bug do broker
em execução. Corrigir somente qualificação crate::mqtt::store e repetir o
mesmo filtro. Não alterar oráculos para mascarar o erro de compilação.
Review também exige recusar elapsed regressivo no input fake por instância,
sem last_elapsed global que rejeite amostras reais concorrentes legítimas;
preparar RED desse caso e proteger o piso lógico por operação atômica.

## Revisão v1.5 após RED de intenção, antes do fix

Após corrigir somente o path do inicializador, RED p227e_intent_ executou7
casos:5FAIL esperados/2controlesPASS, exit1,86scompile/9,58stest. Falharam:
newcopyMayHaveSent em vez dePrepared; restorePreparedvencido ainda replay;
fresh replayDUP1; permit positivo não reservava tentativa; input fake elapsed
regressivo aceito. Controles: MayHaveSent expirado preservado e R0 não marcava
tentativa. Isso é evidência de asserção, separada do compileFAIL anterior.

Agora corrigir fases, ID/metadata/geração no permit, original/default legado,
validação de Prepared e input fake. Marcar intenção só se R>0. Testar falha
WAL sem token/mutação autoritativa; resultado físico incerto não deve exigir
rollback falso no arquivo. Acrescentar teste de fonte inválida test-only e
piso atômico de resultados, sem recusar amostras reais concorrentes antigas.

## Revisão v1.6 antes da poda live e fixtures de escrita

GREEN dos17 testes de clock/intenção,33,74scompile/3,72stest. Ainda não é
aceite final: cópias Prepared vencidas devem liberar quota também no tick,
não só no reconnect. Coordenador autoriza candidato de estado durável E
Live, removendo Prepared vencido, drenando pending_replay antes de offline,
com uma barreira; publicar Live/deliver somente depois do commit. Falha WAL
conserva ambos os estados autoritativos. MayHaveSent/PUBREL não expiram.

Packet ID, geração e deadline não bastam se uma fila velha sobreviver à
reutilização do mesmo ID com metadata igual. Cada nova cópia expiring QoS1/2
recebe identidade crescente por sessão, persistida no v16 e no Delivery;
Prepared exige essa identidade. Legado MayHaveSent mantém identidade ausente.
Limite/overflow falham fechado, sem wrap/reuso. Permit exige correspondência
exata de geração, ID, identidade e metadata; delivery obsoleto é suprimido,
sem apagar ou autorizar obrigação nova. Sem nova fila/canal/quota pública.
Preparar RED de poda/quota1 e rollback antes do fix, teste de reutilização
forçada com metadata igual e falha WAL de Prepared sem token.

Para provar send_delivery real, adicionar somente APIs cfg(test), por
instância: Router::start_with_expiry_clock_for_test(path,auth,metrics,limits,
Arc<ExpiryClock>) compartilha o mesmo clock com store/handler; builder
with_expiry_hook_for_test(Arc<dyn Fn()->Duration+Send+Sync>) executa hook
depois do encode, antes da validação final, e espera a Duration retornada
somente no teste. Sem env/global/flags produção. Validar novamente deadline
monotônico antes de escrever, inclusive após encode demorado. Fuzz é dono
exclusivo do novo expiry_contract_tests.rs; este owner só liga o módulo e
helpers. Testes usam TCP loopback e deliveries reais: mesma faixa1barreira;
cruzamento2;4cruzamentos/3s dão erro limitado/zero bytes; WAL negativo não
escreve nem perde Prepared. Contar commits bem-sucedidos e hooks por caso;
tempo lógico sintético, não ajustar host. Compilar/testar só owner E.

## Revisão v1.7 após RED live, antes de poda/identidade

RED real p227e_prune_2/2FAIL: tick não libera quota1 nem tenta barreira WAL
para remover Prepared vencido;27,72scompile/0,93stest. Dois warnings de
helpers cfgtest ainda sem fixture consumidora, não são ClippyPASS. Corrigir
agora conforme v1.6, preservando os mesmos oráculos. Identidade crescente
será next_expiry_delivery_id na sessão e expiry_delivery_id na cópia;
None permanece para cópias legado/QoS0. Prepared exige Some válido e único
entre outbound, com teto i64::MAX para formato TOML. Reassignment cria nova
identidade no destino. Delivery obsoleto retorna erro interno específico que
handler trata como supressão bem-sucedida, sem discard por packetID reusado.

## Revisão v1.8 antes do canto positivo→vencido e seu fix

Coordenador aprovou outro negativo da mesma fronteira: primeiro permit R>0
marca MayHaveSent; commit/encode seguintes podem cruzar até R0 sem write.
O teste TCP deve reproduzir política anterior de descartar por !dup, antes
da correção. Permit terá disposition explícita: somente Prepared&&R0 ou
QoS0 ainda não iniciado podem ser descartados. MayHaveSent R0 no handler
original DUP0 retorna erro limitado sem novos bytes, preservando replay
incerto. Recovery DUP1 prossegue handshake conservador com TTL0. Não apagar
por expiry/refresh/timeout após intenção durável, nem prometer primeiro byte
observado. Fuzz acrescenta teste direto; owner executa RED antes do fix.

## Revisão v1.9 após RED TCP positivo→vencido, antes do fix

Filtro p227e_ executou29casos:28PASS/1FAIL esperado,29,76scompile/5,74stest.
Poda/quota1, rollback Live/durável, pending_replay antesoffline, identidade
com packetID+metadata iguais e WAL Prepared passaram. Cinco TCP passaram:
mesmafaixa, cruzamento, quatro refresh, deadline3s e WAL antesappend.
Negativo positivo→R0 falhou pois send_delivery retornou Ok pelo descarte
!dup. Corrigir agora disposition explícita e manter o oráculo6º inalterado;
não usar o GREEN parcial para declarar contrato fechado.

## Revisão v2.0 antes da segunda correção de lint e controles QoS2

GREEN29/29 em27,13scompile/5,69stest. Regressões completas dos módulos
router84/84 (34,34s) e store19/19 (0,37s) PASS, filtros sobrepostos ao E.
Clippy --lib --tests -Dwarnings FAIL: expansão de StoredMessage tornou
Packet::Connect376bytes/Publish165, ativando large_enum_variant; comparação
de ID com i64::MAX pede TryFrom. Corrigir cast com TryFrom. Solicitar ao
coordenador exceção localizada para Packet, justificando enum bounded sem
nova alocação, sem alterar parser/framing/Box ou esconder outros avisos.
Somente aplicar essa exceção após autorização. Adicionar controles unitários
QoS2 Prepared vencido sem replay e MayHaveSent expirado que retoma PUBLISH,
PUBREC/PUBREL, reinicia e completa PUBCOMP com o mesmo ID; escopo original.

## Revisão v2.1 após decisão do coordenador sobre enum privado

Não suprimir lint: coordenador autorizou avaliar Box apenas no Will opcional
de Packet::Connect, enum privado. Inventário mostra uma construção no decode
e um consumidor no handler; demais usos são padrões/testes com auto-deref.
Mudar Option<StoredMessage> para Option<Box<StoredMessage>>, Box::new só em
CONNECT com Will e unbox único antes do router. Não alocar por PUBLISH,
alterar wire/framing, API pública, estado durável ou conteúdo do Will.
Reexecutar parser/Will/expiry e Clippy. Os31 testes E, incluindo dois novos
QoS2, passaram em19,89scompile/6,55stest antes deste ajuste de representação.

## Revisão v2.2 após Clippy de todos os testes

Box resolveu large_enum_variant sem supressão; TryFrom resolveu cast.
Clippy agora chegou aos testes e FAIL5: dois assert_is_empty dos novos
controles QoS2 e três unreadable_literal em fixtures VBI P227D existentes.
Corrigir meus asserts para igualdade com Vec vazio. Autor original foi
consultado para somente separadores 2_097_151/2_097_152/268_435_455,
sem mudar valores, bytes de oráculo ou parser. Não mascarar diagnóstico
nem aplicar lint allow global. Reexecutar Clippy e testes pós-Box.

## Revisão v2.3 antes do RED de descarte e fix do baseline CONNECT

Base funcional88906d63c4384961f7a9215945840905f3568b4d. Fulltest do coordenador
encerrou exit1:263PASS/8FAIL/6ignored, compile75s/test66,69s; oito FAIL
connect_contract_tests:306 eram commits1 em vez de0 após novo checkpoint
obrigatório de startup. Não houve outros FAIL. Antes da conexão, capturar
baseline real após startup e comparar exatamente commits depois da recusa,
também status/sessões/retained. Não trocar0 por1, alterar vetores CONNACK ou
aceitar qualquer commit adicional POR CONNECT recusado. Fonte/Cargo agora
liberados pelo coordenador; runner/scripts dirty alheios ficam intocados.

Review independente identificou TOCTOU: prepare_expiry retorna descarteR0,
handler envia DiscardOutbound só com packetID; tick entre comandos pode podar
Prepared, drenar backlog e reutilizarID; descarte velho apaga nova obrigação.
Coordenador aprovou remoção de PreparedR0 DENTRO do mesmo comando do ator,
com commit e dreno atômicos, e eliminação do segundo comando no handler.
MayHaveSent continua não descartável por expiry. Uma barreira, sem quota nova.

MPS também deve descartar condicionalmente a Delivery original: conferir
geração, packetID, identidade imutável e metadata/conteúdo/stage antes de
mutar. Ausência/substituição é NOOP sem WAL nem dreno da nova obrigação;
geração antiga continua recusada. Acrescentar argumento de mensagem ao
comando existente, sem canal/fila nova; clone segue limite4KiB atual.

Para distinguir inclusive QoS1/2 sem expiry com payload/metadata idênticos,
usar contador e campo JÁ presentes no v16 não publicado para TODAS as novas
cópias QoS1/2; QoS0 continuaNone. Nome interno expiry_delivery_id passa a
identificar obrigação geral de saída, não só expiring. Não adicionar campo,
formato17, dependência ou quota. No register/replay, atribuir IDs ausentes
legados no mesmo commit ANTES de expor Delivery; manter stage, packetID,
MayHaveSent e ausência do intervalo original legado. Validação permite ID
sem expiry, exige ID para Prepared e unicidade/counter coerentes. Expansão
de documento continua sujeita a1MB, sem truncamento/elevação de limites.

Preparar RED com assinatura/argumento somente transportados, ainda ignorados
na remoção: R0 precisa remover/drenar imediatamente sem segundo comando;
forçar reuso ID entre retorno/tick/descarte; MPS stale com/sem expiry e
mensagem idêntica não pode remover novo record nem mudar commits/Live;
legacy sem ID deve ganhar identidade antes de replay; WAL R0 falho não
libera quota/token. Depois corrigir e repetir E/codec/store/router/connect
e Clippy testes. Manter todos os RED/infraFAIL anteriores, registrar esta
extensão e congelar novo checkpoint antes do fullgate do coordenador.

## Revisão v2.4 após launcher de RED, antes de corrigir binding

Primeiro compile do filtro p227e_discard_ falhou E0425: inicializador do
argumento expected capturou first_message em padrão homônimo de outro teste,
não no teste MPS que o usa. Isso é erro de scaffolding, não RED de asserção.
Corrigir somente binding no escopo correto, repetir mesmos cinco casos.
Codec agora é ownership Fuzz/P227I somente testes de limites; esta correção
não precisa editar codec.rs, Cargo continua reservado ao owner E.

## Revisão v2.5 após RED real de descarte, antes do fix

Após corrigir o binding, os mesmos cinco casos executaram5FAIL/exit1,
22,49scompile/1,84stest. Confirmaram: R0 não atômico; descarte após tick/reuso
apaga backlog novo; MPS stale apaga cópia idêntica com/sem expiry; legacy
replay exposto sem identidade. Nenhuma alteração de oráculo no RED.

Aplicar agora contrato v2.3. Refatorar helper de descarte para candidato
durável+Live, validando mensagem inteira/identidade/stage antes de mutar,
liberando pending_replay antesoffline depois de uma barreira. prepare_expiry
R0 Prepared chama esse helper dentro do ator; handler só recebe resultado,
sem segundo comando. Controle anterior R0-não-reserva passa a exigir remoção
já concluída em vez de Prepared ainda existente, mantendo proibição de
MayHaveSent por R0. Acrescentar controles WAL e stage PUBREL preservado.
CONNECT terá baseline e snapshots de status/listas antes da conexão, exata
igualdade após recusa, mantendo todos os bytes/respostas e verificações.

## Revisão v2.6 após compile do baseline de listas, antes do ajuste de API

Primeiro compile após fix falhou E0308 nas quatro chamadas admin_list do
baseline. Primeira correção de scaffold também inverteu os argumentos e
falhou novamente E0308; não é FAIL funcional nem troca de oráculo.
Assinatura lida integralmente: kind:AdminListKind, cursor:Option<String>,
limit:usize. Corrigir para kind,None,64, mantendo snapshots exatos antes/
depois da recusa CONNECT. Os dois compileFAIL permanecem registrados.

## Revisão v2.8 antes do oráculo de identidade na regressão de ordem

GREEN E36/36 após fix (26,03scompile/7,45stest). Regressão router apontou
um FAIL configured_inflight_defers_and_drains_without_losing_order: compara
StoredMessage inteira com a entrada sem ID, mas a cópia nova agora recebe
Some(2). Não remover a comparação ou ignorar payload/metadados. Atualizar
expected com identidade2 e verificar counter2, preservando igualdade integral
do restante e todas as asserções de ordem/quota/packetID. É ajuste explícito
do novo contrato interno autorizado, não mudança da sequência observada.
