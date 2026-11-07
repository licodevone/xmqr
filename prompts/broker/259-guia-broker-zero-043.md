# P259 v1.0 — percurso de construção do broker até 0.43.0

## Entrada verificada

Pedido: continuar os passos desde o zero até o projeto concluído como 0.43.0.
Data: 2026-10-30, America/Sao_Paulo. Repositório alvo: xmqr, independente
de xmqr-client e xmqr-admin. HEAD observado: 7c7a989e2eb567295e4674cc5303af19e13bce1e.
A tag local v0.43.0 resolve para db472bc64558bf0e376a902b7780a259247c5149.
O manifesto corrente também declara 0.43.0, mas HEAD contém trabalho posterior.
Preservar alterações existentes em docs/chat e os arquivos não rastreados P257.
AGENTS, contrato-base, contexto, cobertura, CONTRIBUTING, VERSIONING, plano,
nota 0.43.0 e registros P227/P228 foram consultados. Cabeçalhos antigos
descrevem checkpoints históricos; não são o estado final.

## Objetivo e escopo

Entregar um guia de execução e estudo de ponta a ponta, com preparação,
primeiro checkpoint compilável, arquitetura, incrementos MQTT 3.1.1/5,
transportes, migração v16, validação e reprodução isolada da fonte exata.
É uma entrega documental: a implementação integral de um segundo broker
não é alegada por escrever os passos. Não substituir o repositório existente.

Arquivos autorizados: docs/guia-broker-do-zero-0.43.0.md, README.md (link),
prompts/registros/P259-guia-broker-zero-043.md e histórico diário do chat.
O catálogo de prompts será extraído da árvore Git da tag, com links locais
e ponteiros para leitura na revisão exata; incluir suplementos P227/P228B.
Guia orientado à construção, não apenas uma instrução de clone.

## Requisitos

- Separar ordem didática proposta, histórico verificado e reprodução exata.
- Não confundir número de prompt com versão; nem broker com client/admin.
- Preservar limites, filas limitadas, gerações, ACL e commit antes do ACK.
- Explicar dependências e módulos sem inventar marcos anteriores ao histórico.
- Dar objetivo, trabalho, teste e critério de saída a cada etapa.
- Fornecer comandos completos para checkout isolado/build, laboratório local
  e gates, indicando pré-requisitos Linux/WSL e fontes dos pares de aceitação.
- Incluir prompt reutilizável e sequência completa MQTT5 até P227/P228.
- Explicar backup15, estado16, marcador de perfil separado e rollback.
- Nenhum commit, push, tag, release, instalação ou início de serviço nesta tarefa.
- Exemplos didáticos não podem ser apresentados como broker final implementado.
- Evidência histórica 69/69 e 311 testes deve ser rotulada como histórica.

## Aceite e validação

Conferir links locais do guia e presença na tag dos caminhos usados como
referência 0.43.0; conferir catálogo contra git ls-tree. Verificar fences,
estrutura dos passos, SHA da tag, fonte dos pares e comandos contra scripts.
Compilar/verificar o checkpoint Rust mínimo em temporário se os pré-requisitos
permitirem; registrar indisponibilidades. Revisão independente de legibilidade
conforme doc-coauthoring; corrigir problemas após revisar este prompt.
Não executar a campanha integral do broker por uma mudança documental.

## Compatibilidade e migração

Nenhuma alteração em runtime, manifest, lock, estado ou configuração ativa.
Os comandos são instruções para ambientes isolados do leitor. Formato v16
e suas limitações devem seguir a nota publicada. Registrar resultados reais
em P259 e atualizar o histórico antes da resposta final.
