# P227 v1.17 — concluir a fase 6 de MQTT 5

Preparado em 18 de outubro de 2026 antes das alterações. Pedido explícito:
investigar por que a fase6 permanece parcial e finalizar as entregas e o
aceite integrado 6A–6D, preservando broker, client e admin independentes.

## Entrada e isolamento

Broker0.42.0, client0.36.0 e admin0.10.0 publicados. Broker HEAD62f40b0;
client HEADb9f46cb com distribuição da bridge C128 em alteração por outro
escritor. Essas alterações pertencem ao trabalho existente: não sobrescrever,
incorporar em commit próprio, reverter, retag ou publicar código alheio.
Admin mantém core pin9215d4c/estado v15; não repinar por diferença de versão.
Estado atual e remotos devem ser reconferidos antes de cada commit/build.

## Diagnóstico e requisitos

Confrontar M01–M10 da matriz global e os critérios de saída 6A–6D com código,
testes e a norma OASIS MQTT5. Separar falta de implementação, defeito,
evidência pendente e extensão opcional. O número de prompts incrementais
não prova fechamento. Não retirar um requisito para tornar o checklist verde.

6A: matriz por contexto/propriedade/código de erro, limites, coexistência
3.1.1 e duas implementações externas. 6B: migração, expiração, Will Delay,
takeover/restart/crash sem perda silenciosa, obrigações QoS duráveis. 6C:
negociação bilateral, backlog, QoS0/1/2, aliases/reset e metadados duráveis.
6D: opções de assinatura, IDs, shared/failure/fairness e decisão explícita
sobre os mecanismos AUTH suportados; sem confundir suporte PLAIN limitado
com todo mecanismo possível de autenticação estendida.

## Frentes e arquivos

Auditorias paralelas somente leitura inicialmente: 6A codec/propriedades;
6B/6C estado/fluxo; 6D assinaturas/autenticação/client. Coordenador reúne
lacunas e reserva arquivos antes de autorizar implementação. Cada correção
terá subprompt P227A/B/C com requisito, teste negativo e owner, preparado
antes de editar código. Um arquivo não terá dois escritores simultâneos.

Escopo de fechamento: fontes/testes pertinentes dos três repositórios,
scripts de aceite, docs/phase6-acceptance.md, conformance/mqtt5-status.md,
evolution-plan, plano-paridade-mosquitto, registros e documentação de versões.
Não modificar a bridge C128 nem seus arquivos compartilhados sem coordenação.
Fases7/8/9 não são implementadas como desvio para esconder falha da fase6.

## Validação e falhas

Gates locked fmt/test/Clippy/release/inventário; testes wire independentes e
negativos, Mosquitto e Paho, regressões TCP/TLS/mTLS e cenários de crash em
estado descartável nativo Linux/WSL, TMPDIR=/var/tmp. Identificar fontes,
ELFs/hashes, duração e resultados; não depender de binário alterado durante
a campanha. Recursos locais de teste com portas efêmeras e nomes próprios.
Nunca tocar serviços, firewall, firmware, estado ou segredos do operador.

FAIL deve permanecer registrado. Antes da correção, revisar o subprompt;
depois repetir gates afetados. Ausência de pré-requisito é BLOCKED, não PASS.
Não instalar ferramentas ou alterar configuração global só para testar.
Não inferir power loss, estabilidade de dias, SLA ou conformidade integral
por uma campanha finita. Requisitos abertos impedem fechar o respectivo gate.

## Aceite e distribuição

Somente marcar 6A–6D concluídas com matriz requisito→teste→resultado e fontes
exatas, decisão das capacidades opcionais e limitações coerentes. Consolidar
diagnóstico e resultados reais no registro P227. A leitura independente da
matriz deve distinguir entregue, limitado e ausente sem consultar o histórico.

Commit/push das alterações próprias aceitas. Mudança de runtime exige marco
independente validado, tag imutável, prerelease proporcional, .debUbuntu26amd64,
imagem Docker numerada em lepinheiro100, notices originais, SHA/proveniência
e conferência remota. Não mover latest/tags existentes; docs/testes sem
runtime novo não justificam versão artificial. Não anunciar publicação antes
da verificação. MIT própria e licenças dos terceiros preservadas.

Fonte normativa: https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html

## Revisão 1.1 antes das correções e do executor integrado

Auditorias identificaram VBI não mínimo em MQTT5, seleção compartilhada com
contador global que pode privar grupos intercalados, e publicação antecipada
do Will no takeover sem aplicar Message Expiry. Subprompts P227A/P227C devem
reproduzir RED e corrigir sob ownership exclusivo codec e router/store.
Cache transitório por grupo é admissível sem migrar formato15: limitado e
podado pelas assinaturas existentes, clonado no candidato e sem avançar após
falha de commit. Fairness vale durante a vida do processo, não através de
reinícios contínuos; obrigações QoS permanecem duráveis.

O client ainda não possui journal inbound; C110 o apontava explicitamente
como condição aberta de M03. C129 será implementado em clone isolado, com
subscription-state-dir existente, journal privado limitado, fases antes de
ACK, retomada só com identidade e Session Present coerentes, e testes reais
de crash/erros. Autorizar correções restritas do fork rumqttc vendor v5 e
registro XMQR-PATCHES, preservando licença/copyright Apache originais. Não
mudar padrão nem 3.1.1, dependências ou arquivos da distribuição C128 alheia.
Janela stdout→journal pode duplicar saída; não prometer transação de negócio.
Publisher serial com um inflight é limite MQTT válido, não requisito de
pipeline por desempenho; backlog/negociação bilateral continuam gates.

Coordenador pode criar scripts/verify_phase6_acceptance.py e testes próprios
para agregar fixtures vigentes por critério, versões/hashes/fontes limpas,
resultado/tempo/marker real e recusa de skips silenciosos. Excluir fixtures
historicamente substituídas (por exemplo P152 shared indisponível), não casos
que falham no contrato vigente. Problemas externos de Topic Alias devem ser
classificados como limitações, nunca interop PASS por capturar a falha.

Paho2.1.0 não está instalado localmente. A CI existente já usa instalação
isolada para seu gate; usar essa execução como evidência real quando for da
fonte exata, sem alegar teste local. Ausência local permanece BLOCKED. Não
instalar pacote global nem reiniciar WSL. A configuração WSL emite aviso
automount.options alheio, fora do escopo. Binários default observados eram
broker0.41.0/client0.37.0C128, não os marcos0.42/0.36: rebuild final e hashes
reais obrigatórios em cópias isoladas, sem promover esses caches a aceite.

## Revisão 1.2 antes da campanha de crash

Adicionar scripts/verify_phase6_crash_matrix.py e testes determinísticos do
executor. Campanha nativa usa cópia explícita do broker, portas efêmeras e
estado privado em /var/tmp: três repetições de replay QoS1 com DUP/mesmoID,
inboundQoS2 antesPUBREL/outboundQoS2 depoisPUBREC, MessageExpiry após queda
e WillDelay/MessageExpiry após recuperação. SIGKILL só no filho criado pelo
harness; não é queda de energia. Confirmar bytes/metadados, SessionPresent,
ausência de entrega prematura e retained expirado. Relatórios só hashes,
versões, tempos/resultados, sem logs, credenciais ou estado bruto.

Não acrescentar pipeline de publicação apenas para cumprir uma suposição
de desempenho. A suíte aceita limites anunciados e precisa comprovar backlog
e progresso dentro deles. Golden migration deve distinguir fixtures antigas
reais de versões reescritas sinteticamente. O aceite não chamará o segundo
caso de validação de todos os dados históricos possíveis.

## Revisão 1.3 antes da prova independente de autenticação

M10 foi definido como decisão de mecanismo, não obrigação de implementar
todo desafio SASL. PLAIN inicial sobre TLS/mTLS e reautenticação explícita
da mesma identidade são o recorte existente. Criar fixture independente
scripts/verify_phase6_paho_auth.py com Paho2.1.0: CONNECT com método/data,
CONNACK coerente, pub/sub, senha errada e método desconhecido, em TLS e mTLS.
Sem username_pw_set para não mascarar o teste pelo caminho de senha comum.
Reautenticação seguirá rotulada como wire/client próprio, não Paho externo.
A campanha usa certificados/segredos efêmeros, CA/SAN verificados e não
anexa dados privados. CI que já instala Paho isolado deve executar o gate
agregado e guardar relatório sanitizado; ausência local segue BLOCKED.

## Revisão 1.4 antes de obter o peer independente isolado

Sem Paho instalado localmente, usar checkout separado do repositório oficial
eclipse-paho/paho.mqtt.python na tagv2.1.0 sob .artifacts/p227-paho-mqtt-python.
Registrar commit exato e textos de licença originais. Acrescentar somente seu
diretório src ao PYTHONPATH do subprocesso de teste, sem pip/install global,
sem copiar a biblioteca para o runtime XMQR e sem executar setup/hooks.
Isso transforma a dependência do teste em insumo isolado e rastreável;
não permite alegar que o pacote passou antes de executar os cenários.

## Revisão 1.5 antes de ampliar o executor integrado

Integrar o harness P227C de fairness/Will ao registro de fixtures, com relatório
exclusivo. Conferir versões dos cinco binários contra os manifests próprios,
não apenas igualdade debug/release do client. Identificar o módulo Paho pelo
arquivo e SHA/version usados, preservando seu licenciamento, sem instalar.
Adicionar testes determinísticos para divergência manifest/binário e marker
negativo; nunca aceitar NOT_PASS como evidência positiva. Incluir C129 após
entrega do agente, sem tocar a distribuição C128 ainda em alteração alheia.

Auditoria normativa confirmou alias numérico válido ainda não mapeado com
TopicName vazio: §3.3.4 caso3a exige diagnóstico0x82, não0x94. P227D terá
prompt próprio, RED antes da correção e enum distinto em codec/mod.rs;
zero/excesso permanecem0x94. Não alterar mapeamento válido ou quotas. A
matriz só promove esse requisito após repetir o wire na fonte corrigida.

Pedido do mantenedor autoriza seguir às fases seguintes somente depois do
aceite efetivo da fase6. Respeitar dependências e preparar prompts de cada
fatia; fase7 já aceita em seu contrato, bridge/fase8 segue pendências reais.

## Revisão 1.6 — contrato CLI dos harnesses

Revisão de integração encontrou `--label` obrigatório no harness VBI,
omitido pelo registro do executor. Corrigir o argumento antes da primeira
campanha agregada e adicionar teste de contrato; ausência daria argparse
exit2, não uma falha MQTT. Adicionar P227D com labelcandidate explícito,
novo relatório exclusivo e marker próprio depois da entrega do agente.

## Revisão 1.7 — revisão independente do executor

Leitor independente reproduziu falsos positivos puros para NOT_*_PASS e
SKIPPED seguido de PASS; mock demonstrou stderrBLOCKED ignorado. Corrigir
antes do aceite: negativos dos dois canais, markers específicos vigentes,
descendentes remanescentes no grupo privado mesmo em exit0, e testes desses
contratos. Capturar stdout/stderr em pipes com orçamento observado em leitura,
sem permitir arquivos temporários crescerem até timeout. Registrar estágio
e errno sanitizados nas exceções, nunca mensagens privadas completas.

Identificar também versões/hashes de Mosquitto/OpenSSL e módulos Paho
client/properties/packettypes efetivos; não chamar hashde__init__ hashdalib.
Primeira campanha D/client036 ficouBLOCKED/OSError antes dos cenários;
não reinterpretar esse resultado. Diagnóstico separado viu preflightPASS e
gitWSLdirty vs gitWindowsclean nos clones Windows. A opção por chamada
core.autocrlf=true resolveu o status sem diff real de fonte; alinhar só
configuração Git local dos clones de teste ao checkoutWindows, preservando
detecção de mudanças reais e sem configurar global/alterar árvore do operador.

## Revisão 1.8 — retorno real dos contratos do executor

Primeira tentativa de testes adicionais não iniciou Python por falha de
conexão WSL/Service/0x8007274c; nenhuma reinicialização/configuração feita.
Repetição segura executou14testes:13PASS/1FAIL. O FAIL esperava motivo
success_marker_missing para NOT_P227_PASS, que agora é corretamente
rejeitado antes por negative_marker_present. Atualizar somente a expectativa
do diagnóstico; manter obrigatório statusFAIL. Repetir todos os contratos.
Mapear markers específicos reais, inclusive duas linhas cross/sessions e
variante retain_handling sem homologar Mosquitto ausente por opt-in.

## Revisão1.9 — diagnóstico sanitizado da campanha ampla

Dall4 executou68fixtures e falhou em6, preservando fontes/ELFs. Quatro
vetores antigos têm diagnóstico reproduzido emP227H; VBI/aliasReason deram
nonzero antes de cenários, mas repetidos isolados passaram. Não converter
repetição emPASSretroativo. Adicionar somente tipo de exceção permitido e
última linha de stack (número) ao metadata de falha, nunca texto de exceção,
paths arbitrários, payloads/logs. Contrato unitário deve impedir divulgação.

## Revisão1.10 — migrações reais no aceite integrado v16

Antes de alterar o executor: substituir seu gate de formato corrente A19
pelo novo A21, preservando o script/histórico v15. O formato16 exige provar
seed real15, migração sem inventar intervalo original, backup/restore16 e
recusa pelo executável15. Integrar também a migração real do journal inbound
v1→v2 do client, usando o harness C131 com teardown corrigido após seu aceite.

Adicionar --legacy-broker e --legacy-client explícitos. São insumos separados,
identificados por versão/SHA antes e depois, sem comparar sua versão com o
manifest corrente. Ausência bloqueia os gates6B correspondentes, não os omite
nem afeta seleção6A/6C/6D. Não obter binários implicitamente, construir estado
antigo alterando versão sintética ou aceitar artefato mutável. Relatórios
exclusivos por harness, sem logs/segredos; testar contratos de argumentos e
prerequisitos. A21 e journal migration só recebem PASS após execução real.

## Revisão1.11 — isolamento do executor após revisão independente

Revisão identificou herança de P147_MOSQUITTO_PORT, opt-in antigo que faria
uma fixture publicar/assinar em serviço externo. Remover esse seletor do
ambiente dos filhos, preservando PATH/PYTHONPATH isolado e nunca consultar
serviço do operador. Adicionar contrato sem rede para a sanitização.

execute cria sessão privada, portanto KeyboardInterrupt após Popen não é
propagado automaticamente aos descendentes. Proteger captura com limpeza
em exceções BaseException, incluindo encerramento do grupo privado e pipes,
antes de propagar interrupção. Testar com interrupção determinística e filho
real próprio. Nenhum kill de serviço global ou processo não criado pelo gate.

## Revisão1.12 — CI integrada rastreável com peers independentes

Preparar workflow manual phase6-acceptance para executar o coordenador em
Ubuntu26 descartável com Rust1.99, OpenSSL/Mosquitto e Paho2.1 isolado.
Receber SHAs completos dos peers client/admin e legacies; validar formato
antes de checkout, não interpolar inputs em comandos de shell. Os defaults
legados são commits públicos históricos, nunca branch móvel. Checkouts
ficam em integrations/ dentro do workspaceCI, três projetos com nomes que
o executor espera e legacies separados. Não instalar nada no host do operador.

Compilar fontes exatas para todos os binários exigidos e guardar manifesto
ELF→commit/SHA/version, ferramentas e inputs. Executar contratos do runner,
A21 e journal migration pelo agregador sem skip; salvar JSON sanitizado
mesmo após FAIL. Inputs válidos não são aceite; workflow preparado é NOT_RUN
até dispatch real e confirmação do run/artefatos. Nenhum placeholder ou
commit clone/cherry-pick inexistente no GitHub pode substituir fonte pública.

## Revisão1.13 — propriedade Git no containerCI Ubuntu26

CIadminA22 observou FAILreal exit128 detected dubious ownership emUbuntu26/
Git2.53 apóscheckoutv4. Workflowintegrado usa o mesmo container e consulta
rev/status dos repositórios; cancelar somente seu run39141241671
para evitar consumir todos os builds antes desse bloqueio conhecido. Não
chamar o cancelamento de falha MQTT ou PASS. Preservar o FAIL do jobadmin.

Configurar safe.directory via GIT_CONFIG_COUNT/KEY/VALUE só no ambiente do
jobCI, com os seis caminhos EXATOS de checkout (cinco projetos maisPaho)
derivados degithub.workspace. Provar rev/status limpos antes de compilar,
guardar as revisões no relatório inicial e usar artefatos exclusivos.
Sem wildcard, configuraçãoGit global, mudança no host ou desativação geral
da proteção. Contratar YAML/AST/paths e repetir dispatch de commit público
exato; mudança só de CI não altera ELFs/testes do runtime043. Admin segue
seu promptA22 e gates próprios, fonte011 será identificada porSHA.

## Revisão1.14 — artefatosJSON ocultos não podem desaparecer

AdminA22 confirmou annotationNo files found no upload-artifactv4 para
.evidence apesar do gatefuncionalPASS: arquivos ocultos são excluídos por
padrão. Cancelar somente runintegrado39142094084 antes de perder relatórios;
registrar cancelamento, não falhaMQTT. Preparar include-hidden-files:true
somente com lista EXATA dos13JSON sanitizados previstos, nunca pasta inteira
ou wildcard amplo. Exigir presença/JSONparse desses arquivos depois do PASS
do coordenador; missingartefact é erro, não aviso. Falhas continuam com
uploadalways dos relatórios parciais existentes. Testar seleção/AST e
actionlint; repetir dispatch da fonte final com peeradmin corrigido2f3609f.
Sem src/Cargo/ELF/serviços do operador alterados por esta correção de CI.

## Revisão1.15 — raiz de estado nativa para as três fixtures de durabilidade

O run integrado 39162215519 na fonte 1574ab9 concluiu 66/69 cenários
PASS. VBI, aliasReason e sharedWill encerraram com exit2 antes de criar seus
JSON. As três exigem `--state-root` em filesystem Linux nativo; no container
Ubuntu26, `/var/tmp` é overlayfs (reprodução local), incompatível com o
preflight dessas fixtures. Tratar essa causa como hipótese até o rerun.

Antes de modificar o coordenador/workflow, registrar este FAIL e preservar
seu artefato. Adicionar `--state-root` explícito ao coordenador, repassando-o
somente às três fixtures e mantendo `/var/tmp` como default local. No CI,
criar um diretório privativo dentro do workspace montado pelo host, verificar
que `stat -f -c %T` retorna filesystem permitido e passar esse caminho ao
coordenador. Falhar claramente se não houver filesystem nativo; nunca
relaxar a exigência de disco durável nos oráculos ou alegar PASS por skip.

Testar contratos e YAML; executar novamente os 69 cenários com os mesmos
peers e legacies por SHA, baixar/validar os 13 JSON, registrar run/revisão,
resultados e limitações. Só marcar 6A–6D após todos os gates exigidos PASS.

## Revisão 1.16 — fechamento com fontes e artefatos imutáveis

Pedido do mantenedor: resolver as pendências apontadas. Congelar o candidato
broker em `db472bc64558bf0e376a902b7780a259247c5149`, cuja CI padrão
39164202189 passou; a campanha integrada 39164217059 continua pendente.
Não transformar o envio deste prompt ou uma repetição local em aprovação da
campanha remota. Verificar os peers efetivos no manifesto baixado: client
0.38.0 e admin 0.11.0, incluindo o harness administrativo corrigido.

Antes de fechar documentos, baixar e validar os 13 JSON sanitizados, os
69 resultados, fontes limpas e hashes estáveis. Confrontar M01–M10 com
fixtures executadas e manter explícitos os limites de AUTH, aliases externos,
fairness, stdout/journal e crash de processo. Preservar cada FAIL anterior.
Uma alteração exclusivamente documental posterior não muda a fonte dos
ELFs, não exige bump artificial e não permite mover a tag aceita.

Revalidar o pacote Ubuntu 26 amd64 produzido pela CI dessa fonte e executar
upgrade/recusa de estado16/rollback por backup15 em container descartável.
Imagens Bookworm devem declarar VCS_REF da fonte congelada, ter notices e
passar testes próprios antes de publicar. Não instalar .deb Ubuntu no host
nem em Bookworm. Após os gates, tag anotada imutável v0.43.0, prerelease,
Hub numerado e download/conferência dos anexos e digests remotos.

Arquivos de coordenação: registro P227/P228, docs/phase6-acceptance.md,
docs/evolution-plan.md, docs/plano-paridade-mosquitto.md,
docs/conformance/mqtt5-status.md e mqtt5-property-matrix.md, README,
CHANGELOG, VERSIONING, SECURITY e nota 0.43.0. Distribuição P228B tem owner
separado. Não editar Rust, dependências, bridge, serviços ou segredos nesta
fatia. Se surgir falha nova, preservar evidência e revisar prompt antes de
qualquer correção. Marcar a fase 6 somente depois da aceitação efetiva.

## Revisão1.17 — registrar os peers efetivos da campanha remota

Os13JSON do run39164217059 foram baixados e conferidos: brokerdb472bc,
client040/501cde2ffbae6985f033ed8be60d9ad6dd8c18c4 e admin4483a35;
69/69PASS169,757s, três verificaçõesunchanged=true. Portanto substituir a
referência038 na tabela de seleção FINAL pelo client040 efetivamente
compilado/exercitado na CI. Preservar Eall8 como campanha local038 distinta,
sem atribuir seu tempo/ELF ao040. Não modificar inputs, fontes ou oráculos.

O helper administrativod27d67d5 confere com4483. Hashes dos ELFs exercitados
constam no build-provenance e coincidem com os do relatório. Antes da
publicação, confirmar conclusãoSUCCESS do run (post-cache ainda em execução
neste checkpoint). AnexarZIP somente dos13JSON validados, com checksum,
sem diretório de estado. Registrar fonte e hashes dos artefatos publicados.
