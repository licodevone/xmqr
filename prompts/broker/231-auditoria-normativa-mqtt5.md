# P231 — base rastreável da auditoria normativa MQTT 5

ID/versão: P231 v1.5. Data: 2026-10-18.

## Entrada e autorização

Pedido do mantenedor: continuar a auditoria, gerir modelos por tarefa e fazer
commit/push, tags e releases quando justificados. Broker limpo em
`76d3cbdf48b8c6ab1ac74b29fc7bb00eb16ad1ac`, igual a origin/main;
runtime 0.43.0. A fase 6 está aceita no contrato finito, não certificada.
Client/admin são repositórios independentes, sem autorização implícita para
incluir trabalho paralelo não revisado. Não tocar em segredos ou instâncias.

## Objetivo e arquivos

Criar inventário reproduzível dos identificadores normativos presentes no
HTML oficial OASIS MQTT 5 OS de 2019, sem republicar o texto da norma nem
relicenciá-lo como MIT. Arquivos desta fatia: este prompt, script/testes
`scripts/mqtt5_normative_inventory.py` e `scripts/test_mqtt5_normative_inventory.py`,
catálogo JSON e guia `docs/conformance/mqtt5-normative-audit.*`, registro P231.
Atualizar somente o link pertinente em `docs/conformance/mqtt5-status.md`.
Adicionar CI isolada `.github/workflows/mqtt5-normative-inventory.yml` para os
contratos Python offline e consistência interna do catálogo versionado. Essa CI
não baixa a norma nem substitui check contra a fonte com hash observado.

O inventário conta IDs, não requisitos obrigatórios aplicáveis ao servidor:
deduplicar referências/apêndice e não deduzir MUST, papel ou conformidade pela
mera presença de um ID. Todos os IDs começam com aplicabilidade por papel
`UNREVIEWED` e estado `UNREVIEWED`; nenhuma porcentagem de conformidade.
Guardar URL, SHA-256 e tamanho da fonte. HTML integral somente em artefatos
locais fora do Git. Rejeitar fonte vazia, encoding inválido e catálogo divergente.
Usar estritamente o charset declarado no HTML (UTF-8 ou windows-1252), sem
substituição silenciosa. A primeira sondagem UTF-8 falhou com
UnicodeDecodeError no byte 0xb7/posição 51173; preservar esse resultado e
confirmar a declaração real antes de extrair. Não interpretar isso como erro MQTT.
Revisão independente Luna apontou casos ainda não cobertos: charset falso em
comentário/corpo, declarações conflitantes, JSON com chaves duplicadas e bool
aceito como inteiro por igualdade Python. Acrescentar vetores RED antes de
corrigir: ler charset somente em meta do head, rejeitar conflitos e comparar
JSON com tipos exatos/chaves únicas. Reconhecer metadados não autentica fonte.
RED efetivamente executado: 15 métodos, 5 falhas (comentário/corpo como duas
subfalhas, conflito de charset, chave duplicada e bool/inteiro), exit 1.
Corrigir agora somente os contratos identificados e repetir a suíte e check
do catálogo oficial sem regenerá-lo, preservando hash e contagem observados.
A primeira correção não chegou a executar testes: parêntese incorreto na chamada
json.loads produziu SyntaxError na linha 179, exit 1 em suíte e check. Corrigir
a sintaxe e repetir; não registrar esse resultado como falha de MQTT ou PASS.

## Gestão de modelos e revisão

Luna/high: localizar evidências já existentes, somente leitura.
Sol/high: revisar um pequeno grupo de lacunas candidatas contra OASIS e código,
somente leitura. Coordenador integra, valida e registra modelos efetivamente
acionados, sem alegar troca automática do modelo principal. Escalar ambiguidade
antes de concluir; revisão estática não vira teste executado. Não criar agentes
extras se a tarefa não precisar, nem editar configuração global de modelos.

## Critérios de aceite e validação

- Fonte oficial consultada; extração determinística, IDs únicos ordenados
  numericamente, localização de origem sem texto normativo copiado.
- Testes sintéticos independentes: IDs divididos por tags/linhas, repetição,
  ordenação, falsos positivos, fonte inválida, deriva de catálogo e separação
  dos papéis broker/client. Metadados não equivalem a cobertura executada.
- Revisar total observado e limitações; não declarar exaustividade de obrigações
  não numeradas ou aplicar requisitos de cliente automaticamente ao broker.
- Registrar achados de revisão com cláusulas e evidência, distinguindo defeito
  reproduzido, candidato e necessidade de mais evidência. Não corrigir runtime
  nesta fatia nem marcar fase global adicional como concluída.
- Rodar testes Python, geração/check do inventário, sintaxe, links locais e
  git diff --check. Rust e serviços não são necessários para catálogo/ferramenta.
- Falhas reais preservadas; revisar este prompt antes da correção correspondente.

## Compatibilidade, publicação e limites

Nenhuma migração, dependência nova, mudança Rust, Cargo, licença ou default.
Autoral MIT preservado; OASIS permanece fonte externa com direitos próprios.
Commit/push somente arquivos próprios após revisão. Não incrementar runtime,
criar tag artificial ou republicar .deb/Docker para mudança de auditoria.
Uma futura correção funcional terá prompt próprio, gates, versão independente
e distribuição testada; tags/releases existentes são imutáveis, sem mover latest.
