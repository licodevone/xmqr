# P227C v1.2 — fairness por grupo compartilhado e expiração de Will no takeover

Preparado em 18 de outubro de 2026, antes de testes novos e correções.
Complementa [P227](227-fechamento-integrado-fase6.md). Pedido autorizado:
concluir a fase6 com evidência real, sem apagar lacunas nem ampliar capacidades
opcionais por acidente. A coordenação reservou router.rs e store.rs para
este agente; codec/mod.rs pertencem a outras frentes.

## Entrada e diagnóstico verificável

Broker0.42.0, HEAD observado35e7fcdf240c8bd9f01f939b16dbe49b52c9728c;
codec.rs tem alterações alheias. Client publicado0.36.0 tem C128/0.37.0
em andamento: não editar ou incorporar seus arquivos. Admin0.10.0/estado v15
mantidos. Binários debug existentes não são aceites deste código: o broker
observado pela coordenação ainda informa0.41.0. Registrar versão/SHA do ELF
efetivamente executado nos gates novos; principal executa a compilação final.

1. `apply_shared_deliveries` usa um cursor global, avançado por publicação.
   Com dois filtros compartilhados independentes e dois membros em cada,
   publicações alternadas A/B podem fazer A observar somente turnos pares
   e B somente ímpares. O módulo2 escolhe sempre o mesmo membro em cada
   grupo. O teste de um único grupo não detecta essa starvation.
2. `register_with_policy_and_delay` resolve o Will anterior no Clean Start
   usando `prior.message` diretamente. Esse caminho não chama
   `will_publication(prior, now)` e perde Message Expiry Interval:0 pode
   ser entregue/retido e1 pode criar retained sem prazo.

## Escopo e invariantes

- Fontes: somente `src/mqtt/router.rs` e o campo transitório aprovado em
  `src/mqtt/store.rs`; testes unitários dos dois contratos no router.
  Um harness específico adicional só se necessário e coordenado.
- Cache de round-robin por chave completa `$share/grupo/filtro`, não por
  ShareName isolado. Preferência por membros ativos e política de capacidade,
  ACL, QoS/RAP/Subscription Identifier, associação e obrigações duráveis
  continuam as existentes.
- O cache será `#[serde(skip)]`, clonado junto ao candidato; falha de commit
  não publica estado ou avança o agendamento autoritativo. Podar chaves sem
  associação em qualquer sessão existente antes de novas seleções; limite
  pelo conjunto finito das assinaturas atuais, sem payloads ou segredos.
  Preservar `shared_cursor` legado. Não há formato v16, nova migração,
  dependência, quota, alteração de pin ou incompatibilidade do admin v15.
- Fairness definida: para membros elegíveis estáveis, alternar escolhas
  independentemente do tráfego dos outros grupos durante a vida do processo.
  Após recovery, os cursores transitórios reiniciam; associações e obrigações
  QoS continuam duráveis. Não prometer fairness através de reinícios contínuos,
  distribuição exata sob alterações de membros ou throughput/SLA.
- Publicação do Will anterior deve calcular o prazo no instante da publicação,
  não no CONNECT nem no prazo futuro do Will Delay. Expiry0 não encaminha;
  expiry1 expira retained. Preservar ACL, cancelamento da obrigação, takeover
  da mesma identidade e commit antes da entrega/CONNACK correspondente.
- Não tocar codec/mod.rs, CI, Cargo, docs gerais, bridge C128, runtime do
  admin, tags, assets, serviços, firewall, hardware ou C:/x81. MIT preservada.

## Norma e limites do fechamento 6D

[OASIS MQTT5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html),
§3.1.3.2.4 (Message Expiry Interval do Will), §3.1.2.5 e §3.3.2.3.3
(prazo/publicação/descartar expiradas), §4.8.2 (um destinatário por filtro,
QoS concedido, retenção do ownership QoS2 e redistribuição QoS1 recomendada).
A norma deixa a escolha de membro a cargo do servidor; fairness é critério
de saída explícito do planejamento XMQR, não uma distribuição estatística
uniforme imposta como MUST pelo MQTT.

M10 permanece uma decisão de capacidade explícita: PLAIN sobre TLS e
reautenticação da mesma identidade existem; desafio/métodos adicionais,
rotação/periódico não serão implementados nesta correção. Não chamar fixture
própria de interoperabilidade AUTH externa nem fechar M10 sem evidência ou
decisão coerente com os critérios originais.

## RED → GREEN e coordenação

Commitar este prompt localmente antes de qualquer alteração nas fontes.
Preparar primeiro testes `p227c_*` sem o fix: dois grupos intercalados com
dois membros; Clean Start/takeover antes do Will Delay para expiry0 e1.
Solicitar janela de Cargo ao coordenador: o agente de codec roda primeiro;
não iniciar build pesado ou usar binário0.41.0 como prova da fonte0.42.0.
O RED real deve registrar as falhas de asserção esperadas, não só compilação.
Revisar o prompt antes do fix após os resultados RED.

Depois, aplicar as duas correções mínimas e acrescentar testes de poda,
rollback do cursor em falha de commit e reinicialização do cache no recovery.
Reexecutar as mesmas regressões até GREEN e as anteriores de shared/QoS1/
QoS2/Will/retained. Coordenador executa fmt, testes locked completos, Clippy
-D warnings, release e inventário no código integrado e executável identificado.
Wire/interop final e distribuição ficam com a coordenação. Nenhum push/tag
ou release por este agente até integração autorizada; registrar PASS/FAIL e
limitações reais, sem alegar perda física de energia ou produção.

## Revisão v1.1 — RED executado antes das correções

O coordenador aprovou o campo transitório adicional em store.rs antes da
mutação, preservando o campo shared_cursor legado (também serde(skip)).
Os três testes p227c_* foram compilados de fonte mqtt-broker0.42.0 no WSL,
TMPDIR=/var/tmp/-j1, sem executar o ELF debug0.41.0. Cargo compilou em32,52s;
testes2,54s, exit1: três FAIL de asserção esperados. Grupos intercalados
produziram [4,0,0,4], esperado[2,2,2,2]; Will expiry0 foi encaminhado e
Will expiry1 foi entregue sem deadline. Não há PASS inferido dessa reprodução.

Agora corrigir somente o estado candidato: cursor por chave completa e
poda no commit (inclui unsubscribe/expiração/revogação sem esperar tráfego
novo); usar will_publication(&prior,now) no caminho Clean Start. Campo novo
não serializado, reiniciado no recovery, sem v16 ou repin. Acrescentar
unitários de poda, rollback em erro WAL e recovery sem cursor mas com
associações/obrigações preservadas. Rustfmt apenas dos arquivos próprios;
GREEN targeted só após coordenação da janela Cargo. A norma foi reconferida:
Message Expiry do Will está em3.1.3.2.4, corrigindo a referência numérica
inicial; não houve mudança do requisito ou do oráculo.

## Revisão v1.2 — campanha blackbox antes de alterar o teste

O fix local foi commitado em10bab601050cb547933d6702e4291fe184e86c8d,
com6/6testes P227C,12/12shared e14/14Will PASS (filtros sobrepostos).
Esse resultado ainda não prova o executável integrado. O coordenador
autorizou somente o novo scripts/verify_phase6_shared_will.py e este
prompt/registro; nenhum novo runtime, codec, CI, versão ou dependência.

Preparar teste wire independente do encoder Rust, reutilizando apenas
helpers raw/lifecycle de fixture existente inspecionada. CLI exige
--broker e --report novos; --state-root default/var/tmp em filesystemLinux
nativo e --label baseline/candidate. Copiar o ELF explícito para diretório
privado, registrar SHA/versão do efetivamente executado e do harness,
remover variáveis MQTT herdadas e ouvir apenas127.0.0.1 em portaefêmera.
Não instalar, reiniciar WSL, tocar serviço/estado/segredos ou pathsalheios.

Casos mínimos: dois grupos A/B independentes, dois membros cada, quatro
publicações por grupo estritamente intercaladas e confirmação por PUBACK
mais leituras delimitadas, cobrando uma cópia por publicação e equilíbrio
2/2 por grupo. Will retido com Delay60/SessionExpiryinfinito e expiry0/1:
takeover ativo CleanStart da mesma identidade, aguardar CONNACK e fechamento
da geração anterior, verificar entrega imediata/ausência e retained antes/
depois do prazo. Usar barreiras MQTT e deadlines monotônicos; não depender
de sleep para ordenar disconnect/register. Espera real pelo expiry1 é
necessária, delimitada e medida. Falhas de asserção devem ter mensagens
estáticas; relatório JSON não inclui payloads, pacotes, logs ou credenciais.

Executar RED em .artifacts/p227-binaries/mqtt-broker-baseline-0.41.0
(versão real antiga explicitada), preservando as três falhas; executar
GREEN somente após o coordenador fornecer o ELF integrado0.42.0 congelado.
Não usar o baseline como prova do0.42, nem assumir GREEN pelo unitário.
Cada cenário tem estado próprio para uma falha não contaminar os demais;
cleanup de sockets/filho/diretório deve ser explícito e constar no JSON.
Relatório exclusivo não sobrescreve FAIL. Falha ambiental é classificada,
não mascara defeito ou vira PASS. Commit local somente dos arquivos próprios
depois da validação e em janela de index combinada com o agente do codec;
push/tag/publicação continuam fora desta tarefa. Avisar argumentos e marker
ao coordenador para integrar o runner, sem editar seu arquivo.
