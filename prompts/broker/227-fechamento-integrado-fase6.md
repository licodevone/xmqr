# P227 v1.0 — concluir a fase 6 de MQTT 5

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
