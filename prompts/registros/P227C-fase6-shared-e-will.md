# P227C — fairness compartilhada e expiração do Will no takeover

Data: 18 de outubro de 2026. Correção coordenada no [P227](../broker/227-fechamento-integrado-fase6.md),
com [subprompt P227C](../broker/227c-fase6-shared-e-will.md) preparado antes das
fontes. Ownership exclusivo: `src/mqtt/router.rs`, campo transitório aprovado
em `src/mqtt/store.rs`, testes internos e este registro. Não foram alterados
codec/mod.rs, versões, CI, dependências, admin, bridge C128 ou client.

## Prompt primeiro e RED preservado

O prompt inicial foi commitado localmente em
`8c630b3570f2d5161f4980cc2c5aa9a377229920`. Sua revisão v1.1 foi commitada
em `ef93dc4` depois do RED e antes dos fixes. Nenhum desses commits foi
enviado ao remoto por este agente.

O RED compilou a biblioteca de `mqtt-broker 0.42.0`, não o ELF debug anterior
0.41.0. Com `TMPDIR=/var/tmp`, `--locked --lib -j1`, os três testes novos
falharam por asserção (exit1; compilação 32,52s; execução 2,54s):

- Dois grupos com dois membros e publicações A/B intercaladas produziram
  `[4,0,0,4]`, contra `[2,2,2,2]`: o cursor global permitia starvation.
- Clean Start/takeover antes de Will Delay encaminhou um Will com expiry0.
- O mesmo caminho publicou Will com expiry1 sem deadline.

Esses FAIL são reprodução anterior à correção, não falha de infraestrutura
ou sucesso inferido do runtime corrigido.

## Correção mínima e limites

Cada chave completa `$share/grupo/filtro` agora tem seu cursor independente.
O mapa `shared_group_cursors` é `serde(skip)`, acompanha o clone candidato e
é podado antes de todo commit, mantendo apenas filtros associados a sessões
existentes, inclusive persistentes offline. O tamanho é limitado pelo conjunto
das assinaturas atuais; grupos removidos não acumulam entradas. A seleção de
redistribuição QoS1 usa a mesma chave, sem alterar preferência por ativos,
capacidade, ACL, RAP, Subscription Identifier ou concessão QoS.

Falha de WAL não avança o cache autoritativo ou entrega a publicação rejeitada.
O campo legado `shared_cursor` foi preservado. Formato v15, migrações e pin do
admin permanecem iguais: nenhuma obrigação durável mudou de representação.
Recovery reinicia somente o agendamento transitório. Fairness vale por grupo
durante a vida do processo com membros elegíveis estáveis; não promete
distribuição exata sob churn nem fairness através de reinícios contínuos.

O takeover agora resolve o Will anterior por `will_publication(&prior, now)`,
como os demais caminhos. A expiração começa na publicação: expiry0 não é
encaminhado/retido; expiry1 recebe prazo e é removido de retained ao expirar.
Will Delay, identidade, ACL e atomicidade de estado/entrega foram preservados.

Referência primária: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html),
§3.1.3.2.4 e §3.3.2.3.3 para expiração; §4.8.2 para shared subscriptions.
A escolha do membro é definida pela implementação; fairness é critério
adicional do planejamento XMQR, não uma exigência de distribuição uniforme
da norma. A revisão v1.1 corrigiu a numeração inicial da cláusula do Will,
sem alterar requisito ou oráculo.

## GREEN local efetivamente executado

Janela de Cargo solicitada e liberada pelo coordenador, depois dos testes do
agente de codec. WSL Ubuntu26, cache compartilhado do broker, `TMPDIR=/var/tmp`,
Rust da toolchain stable, um job. Todas as execuções abaixo usaram
`cargo test --locked --lib <filtro> -j1 -- --nocapture` e terminaram em exit0:

| Filtro | Resultado | Compilação/execução |
| --- | --- | --- |
| `p227c_` | 6/6 PASS | 34,27s / 2,87s |
| `mqtt5_shared_` | 12/12 PASS | 4,65s / 4,42s |
| `will_` | 14/14 PASS | 4,16s / 6,80s |

Os filtros se sobrepõem; os resultados não representam 32 testes distintos.
Os seis novos casos verificam grupos intercalados; chave completa/poda;
rollback em erro WAL; recovery sem cursor mas com associação/QoS preservados;
Will expiry0 e expiry1 no takeover. As regressões incluem QoS1 redistribuído,
fila cheia/último membro, rollback, QoS2 sem redistribuição indevida, recovery,
ACL, retained e Will Delay. O teste antigo de igualdade após recovery limpa
explicitamente os dois campos transitórios antes de comparar estado durável.

Rustfmt foi aplicado somente aos dois arquivos próprios. `git diff --check`
passou. Nenhuma compilação de bins, release ou suíte completa foi iniciada por
este agente nesta janela. O coordenador recebeu a liberação do cache ao final.

## Auditoria 6D e aceite ainda coordenado

M08 já tem opções No Local/RAP/Retain Handling e Subscription Identifier no
router e no client, com fixtures específicas. M09 tem shared ativo/durável e
redistribuição QoS1; esta correção fecha a starvation reproduzida sem atribuir
à campanha uma garantia de fairness após reinícios contínuos.

M10 permanece a decisão explícita de PLAIN inicial sobre TLS/mTLS e
reautenticação solicitada da mesma identidade. Métodos adicionais,
challenge/rotation/periódico não são requisitos implementados aqui. Testes
wire/client próprios de AUTH não são interop externa. A coordenação prepara
peer Paho independente para o CONNECT PLAIN inicial e recusas; esse peer não
é prova de reautenticação externa. Ausência de dependência ou execução deve
ser BLOCKED, não PASS.

Suíte integrada, Clippy, binário congelado/versionado com SHA, wire, crash e
interop pertencem ao coordenador. Este registro é GREEN local, não fechamento
global 6A–6D, publicação, teste de hardware, queda física de energia ou SLA.
MIT própria e licenças de terceiros preservadas. As skills locais
`xmqr-rust-mqtt`, `xmqr-tests` e `xmqr-security-review` orientaram isolamento,
tipos/limites e negativos; não substituem os gates pendentes.
