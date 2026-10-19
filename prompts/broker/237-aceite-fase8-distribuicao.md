# P237 v1.3 — reconciliar aceite e distribuição da fase8/T02

Data:2026-10-19. Entrada brokerfb75667/0.43.0; clientC14845ca641 com
aceite local e CI39300031174 em andamento; C149prepara0.43.0/bridge0.5.0.
AdminA25fonte2b6f245 validada, última release independente0.11.0.
Pedido: finalizar fase8 e seguir com prompts/checklists honestos e distribuição.

Objetivo: confrontar os oito requisitosP235 com implementação, evidência
e entrega remota, corrigindo a defasagem do plano e da linhaT02. A edição
documental não altera a versão do broker nem publica pacote dele sem mudança.

Escopo: docs/phase8-acceptance.md novo, docs/evolution-plan.md,
docs/plano-paridade-mosquitto.md, README e registroP237; fragmento do curso e
HTML local docs/code-guide.html fora do Git, via updater existenteP236, se
necessário para alinhar versões/status. Registrar commit/pushP236 já realizado.
Preservar notas históricas como históricas e links de evidência.

Critérios: matriz requisito→código/teste→resultado→artefato, CI exata deC149,
wire/interop dos ELFs debug/pacote/imagem e recuperação debug, instalação/
rollback descartáveis, tag anotada imutável e seis anexos/digest conferidos.
Só ticar fase8/T02 após esses gatesPASS. Se falhar, manter aberta e revisar
prompt antes de correção, sem apagarFAIL/NOT_RUN. Checklist só registra trabalho
comprovado; não ticar passos manuais do aluno ou alegar ESP32 executado.

Limites explícitos: sem certificaçãoMQTT5 integral/cluster/Windows, sem commit
atômico entre brokers e sem garantia de percurso se intermediário remover
propriedade. Expiração conservadora e cota de um voo por rota permanecem.
Adminweb/statusA25 tem aceite próprio e não é requisito oculto da bridge.

Validação proporcional: links/IDs/checklist e coerência de versões; testes
P236 se alterar guia/fragmento. Sem repetir testes Rust do broker só por texto.
Commit/push documental após aceite, preservando tags/publicações anteriores.

Extensão documentalv1.1 antes da edição: atualizar também os índices locais
fora do Git `../docs/VERSOES-E-EVOLUCAO.md`, `../docs/README.md` (aviso atual)
e `../docs/instaladores/ubuntu26-amd64/README.md`, atualmente defasados em
broker0.42/client0.40. Após conferir releases remotas, copiar os deb/sidecars
do conjunto broker0.43/client0.43/admin0.11 nessa pasta, sem remover versões
anteriores. Preservar histórico e separar adminA25fonte de release0.11.
Registrar hashes/cópias locais, sem alegar publicação desses arquivos foraGit.

Extensãov1.2 antes da edição: alinhar `docs/current-releases-wsl.md`, página
de instalação publicada no Git ainda em client0.41.0, com a entregaC149
conferida. Preservar instruções de estado16 do broker e acrescentar migração/
rollback seguro da bridgeformato2, sem confundir pacoteadmin0.11 com fonteA25.

Revisãov1.3: primeira asserção documental global encontrou corretamente a
frase antiga deC139 que mantinha T02aberto naquele marco, causando falsoFAIL
do verificador de estado atual. Preservar essa história; verificar checkpoint
vigente e checklist/linhaT02 globais, sem exigir apagar registros anteriores.
Nenhum gate funcional ou critério de aceite é reduzido por essa correção.
