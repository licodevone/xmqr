# P227E — relógio lógico de expiração, gates locais concluídos

Data:18 de outubro de2026. Pedido coordenado em P227, após auditoria somente
leitura de M03–M07. O [P130 original](../broker/130-message-expiry-mqtt5.md)
exigia deadline e intervalo original persistidos; havia somente deadline e
subtração de SystemTime, permitindo renovar TTL após recuo UTC.

O [prompt P227E](../broker/227e-relogio-expiracao-duravel.md) foi preparado e
commitado antes das fontes emfc3b40abf1743c49ea57ed9e7c1adf708b55478b.
Revisão após RED/antesfix emef999c0. Revisão v1.2 precedeu correções de lint.
Owner: clock/router/store/mod.rs e testes próprios; codec/fuzz_tests tiveram
inicializadores mecânicos autorizados. Revisão v2.1 autorizou adicionalmente
Box somente no Will opcional do enum privado CONNECT, unbox no handler;
não altera wire/parser/estado durável nem aloca por PUBLISH. Cargo/versão/admin/CI/publicação são
do coordenador; scripts de aceite alheios foram preservados.

## RED preservado

Extração da fórmula UTC-only para clock injetável por instância, ainda sem
aplicar watermark/progresso monotônico. Executado no WSL Ubuntu26, Ruststable,
TMPDIR=/var/tmp, `cargo test --locked --lib p227e_ -j1 -- --nocapture`:
três FAIL de asserção, exit1,64scompile/0,02stest. Live/restore retornaram19
em vez de6; salto adiante seguido de recuo retornou10 em vez de0. Isso é RED
unitário do caminho de cálculo, não campanha wire ou mudança do relógio host.
Avisos temporários do clock ainda não integrado não eram PASS de Clippy.

## Implementação e fronteiras

Clock compartilhado pelo router e handler, com progresso Instant e piso UTC
atômico não decrescente. Sem mutex/disco no cálculo. Saltos adiante avançam;
recuos não aumentam o prazo. Overflow/pré-epoch falham fechado. Intervalo
original acompanha a mensagem; publicação do Will só o preenche quando cria
o deadline. Watermark é candidato/commit, não mutação antecipada do agregado.

Antes de encaminhar cópia com expiry, ator confirma geração e persiste piso
da amostra, liberando permissão com o TTL inteiro. Após encode e antes do
write, checar mesma faixa inteira sem await intermediário: se mudou, renovar
checkpoint em vez de emitir TTL menor não coberto pelo piso durável. Guard
comum testado permite no máximo4tentativas/3s; nenhuma reserva futura. Falha
WAL/timeout não vira permissão, ACK ou descarte silencioso. Não interromper
handshake já iniciado. Persistência da obrigação continua sujeita à vida da
sessão: CleanStart/Expiry0 podem terminá-la legitimamente.

Formato v16 necessário porque novos campos em deny_unknown_fields não são
compatíveis com leitores v15. Leitura v1–v15, gravação v16; original legado
ausente continua None, sem inventar história. Primeiro restore legado usa
UTC disponível; só a partir do checkpoint v16 há piso durável novo. Não
reconstruir downtime físico, bytes possivelmente enviados ou rollback UTC
anterior à migração. Restore v16 parte de max(UTC,piso), progredindo por
Instant. Salto UTC adiante não é revertido para ressuscitar mensagens.

Quotas mantidas, inclusive1MB do documento: expansão que exceda limite falha
fechado, não trunca ou aumenta quota. Admin precisa pin/core16 e provas reais;
rollback ao leitor15 exige backup anterior. Esses gates são do coordenador
e não são PASS por esta implementação.

## Gates locais efetivamente executados

Mesmos três RED passaram inicialmente em0,01s após70scompile. Com integração
e testes adicionais, filtro `p227e_` passou10/10, exit0,56,21scompile/1,56stest.
Cobre live/restore com wallclock recuado; salto adiante; TTL0/U32_MAX/overflow;
faixa commit→encode; guard4/3s; retained/offline/intervalo original e WAL sem
permissão/ownership perdido; migração sintética e campo ausente legado.

Regressões `cargo test --locked --lib <filtro> -j1 -- --nocapture`, exit0:

| Filtro | Resultado | Execução |
| --- | --- | --- |
| `expiry` |13/13 PASS|9,55s|
| `will_` |14/14 PASS|13,61s|
| `receive_maximum` |4/4 PASS|4,12s|
| `reads_v` |3/3 PASS|0,34s|

Filtros se sobrepõem, não somar como casos distintos. Migração é sintética
com dados compatíveis de versões antigas, não fixture produzida por todos
os binários históricos. Rustfmt limitado aos arquivos próprios.

Primeiro Clippy `--locked --lib -j1 -- -D warnings` FAIL com quatro lints:
reload102linhas, serde &u64, QoS sem crases e single_match_else. Prompt v1.2
precedeu correção: exceções locais justificadas por assinatura serde e
transação única, comentário corrigido e iflet; sem supressão global. Segunda
execução PASS, exit0,16,64s. Não executar suíte/bin/release completos por este
agente: permanecem com o coordenador após congelar checkpoint.

## Revisão independente, extensão aprovada e pendências explícitas

Revisor independente confirmou estrutura clock/permit/WAL e identificou uma
fronteira anterior: outbound AwaitPubAck/Rec era persistido antes da fila/write
e todo replay tratado como DUP. A extensão aprovada nas revisões v1.3–v1.9
introduz Prepared/MayHaveSent duráveis. Nova cópia expiring QoS1/2 começa
Prepared; primeira permissão positiva persiste MayHaveSent no checkpoint do
clock. Legado sem marcador é MayHaveSent, sem inventar bytes anteriores.
Recovery de Prepared fresco é DUP0, vencido é removido; MayHaveSent expirado
é DUP1 e preserva handshake, inclusive PUBREL/PUBCOMP. Janela inevitável entre
intenção WAL e write permanece incerteza, não prova de byte observado.

Tick/restore removem Prepared vencido, com candidato durável e Live, uma
barreira antes de liberar quota e entregar backlog. pending_replay precede
offline; falha WAL conserva ambos estados autoritativos. Identidade crescente
por sessão distingue obrigação de packetID reutilizado; permit confere geração,
packetID, identidade e metadata. Delivery obsoleto é suprimido sem alterar a
nova cópia. Overflow de identidade falha fechado (teto i64::MAX/TOML).

Disposition explícita impede apagar MayHaveSent se a primeira permissão
positiva cruzar até R0 antes de escrever: handler original retorna erro sem
bytes e preserva replay incerto. Somente Prepared&&R0/QoS0 não iniciado são
descartáveis. Não é uma promessa de distinguir o primeiro byte físico após
crash; não há reserva de tempo futuro ou licença para apagar QoS já iniciado.

## REDs adicionais e testes TCP por instância

Prompt v1.4 registrou compileFAIL E0433 de launcher: fuzz_tests pertence ao
codec e super::store não existia. Corrigido somente path crate::mqtt::store;
isso não foi tratado como RED de asserção. RED seguinte7casos,5FAIL/2controles
PASS (86scompile/9,58stest): fase inicial errada, replay vencido/fresco,
intenção não marcada e input fake regressivo aceito. Prompt v1.5 antesfix;
GREEN17/17 (33,74scompile/3,72stest).

RED live2/2FAIL (27,72scompile/0,93stest): tick não liberava quota1 nem cruzava
WAL. Prompt v1.7 antesfix. Depois28PASS/1FAIL entre29casos (29,76scompile/
5,74stest): negativo TCP R7→R0 retornava Ok por descarte !dup. Prompt v1.9
antesfix. Mesmo oráculo ficou GREEN29/29 (27,13scompile/5,69stest).

Agente revisor fase3_fuzz criou exclusivamente expiry_contract_tests.rs;
este owner integrou APIs cfg(test) por instância e executou os gates. Seis
testes chamam send_delivery real com TCP loopback privado /var/tmp e bytes
esperados montados independentemente, sem usar encoder/decoder como oráculo:

- Mesma faixa inteira:1checkpoint,1write, TTL7 e recovery piso>=13_000.
- Cruzamento:2checkpoints, reencode TTL6 e piso>=14_000.
- Quatro cruzamentos:4checkpoints, erro limitado e zero bytes.
- Hook após encode espera3,1s: deadline excedido, zero bytes/obrigação mantida.
- WalAppend Error antes append: nenhuma permissão/byte, recovery Prepared.
- R7→R0 após intenção:2checkpoints, erro/zero bytes, recovery MayHaveSent.

Hooks de relógio/delay são cfg(test), após encode/antes da validação final,
não uma medição de fsync lento real. Clock é o mesmo Arc em store/router/
handler, com input sintético; nenhum relógio host foi ajustado. Asserções
de WAL pre-append não generalizam rollback físico para fsync incerto.

Dois controles adicionais QoS2 elevaram filtro E a31/31 (19,89scompile/
6,55stest): Prepared expirado sem replay; MayHaveSent expirado retoma PUBLISH,
PUBREC/PUBREL, reinicia, retoma PUBREL e completa PUBCOMP com o mesmo ID.
Regressões router84/84 (34,34s) e store19/19 (0,37s) PASS antes desses dois
controles, incluindo expiração/Will/ReceiveMaximum/shared/migração/rollback.
Filtros se sobrepõem; não somar como casos únicos.

Clippy posterior --lib --tests -Dwarnings FAIL: enum privado Packet ficou
376bytes/165bytes e comparação de ID pediu TryFrom. Prompt v2.0 antesfix;
coordenador escolheu Box do Will opcional CONNECT, uma construção/unbox,
sem suprimir large_enum_variant (prompt v2.1 antesajuste). Validação final
desse ajuste de representação continua a registrar abaixo.

Segunda chamada --lib --tests após Box/TryFrom avançou aos testes e FAIL5:
dois assert_is_empty nos meus controles QoS2 e três unreadable_literal nos
valores VBI P227D. Prompt v2.2 antesfix: assertions foram convertidas em
igualdade com Vec vazio; coordenador autorizou os três separadores como
integração mecânica sem mudar valores, wire ou oráculos.
Tentativa seguinte de rodar codec no WSL falhou antes de Cargo iniciar,
exit1 Wsl/Service/0x8007274c (timeout de conexão). Não é falha de parser/teste
e não houve kill/restart/alteração de serviços. Rustfmt --check nativo Windows
para clock/router/store/mod PASS após as edições; não substitui gates Linux.

Probe posterior read-only /bin/true no WSL exit0/0,26s, sem ação de restart.
Retry real do mesmo filtro codec pós-Box passou67/67,21,27scompile/0,02stest,
incluindo CONNECT com Will, metadata, framing/VBI e aliases P227D. O primeiro
FAIL de infraestrutura permanece registrado; não foi bug de parser corrigido.

## Checkpoint final local, após Box e integração de lint

Mesmos comandos locked/-j1 no WSL Ubuntu26, Ruststable, TMPDIR=/var/tmp:

| Gate | Resultado | Compile/check | Execução |
| --- | --- | --- | --- |
| `cargo test --lib p227e_` |31/31 PASS|2,70s|7,64s|
| `cargo test --lib mqtt::codec::tests` |67/67 PASS|21,27s|0,02s|
| `cargo test --lib will_` |14/14 PASS|16,21s|7,11s|
| `cargo clippy --lib --tests -- -D warnings` |PASS sem avisos|21,41s|—|

Rustfmt --check e git diff --check PASS. Clippy inclui os testes do novo
arquivo e não suprime large_enum_variant: Box só no Will opcional CONNECT,
sem alteração de API pública ou hot path PUBLISH. Separe estes resultados
dos gates pré-Box router84/store19 e não some filtros sobrepostos.

Owner não executou build de bins/release, suíte completa nem publicação
após este checkpoint. Todo ELF anterior continua anterior, mesmo se tiver
o mesmo número de versão Cargo. Coordenador deve congelar novo ELF/hash e
executar gates integrados/fixture real15→16/admin antes do aceite global.

Suíte completa, wire/artifacts, fixture real15→16, recusa de leitores antigos,
admin pin/backup e distribuição continuam pendentes. Não declarar fase6,
produção, interoperabilidade nova ou tempo físico perfeito. MIT própria e
licenças originais preservadas; skills locais de Rust/teste/segurança orientaram
isolamento e negativos, sem substituir gates reais.
