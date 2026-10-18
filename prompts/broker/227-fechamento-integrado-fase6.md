# P227 v1.4 — concluir a fase 6 de MQTT 5

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
