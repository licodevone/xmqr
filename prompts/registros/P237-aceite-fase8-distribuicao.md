# P237 — aceite integrado da fase8/T02

Prompt [P237v1.2](../broker/237-aceite-fase8-distribuicao.md), original
publicado em38405d3 antes da reconciliação. Contrato finito
[P235](../broker/235-fase8-contrato-integrado.md), implementação C147/C148,
distribuição C149 no client independente. Broker0.43.0/admin0.11.0 não
recebem versão nova por uma alteração documental.

## Preparação, antes da publicação

C14845ca641 terminou seis jobsPASS na CI39300031174, com relatóriosdebug/
pacote lidos: wire33PASS/1NOT_RUN, brokers34PASS, recuperação15PASS e C14723PASS.
C149 acrescentou negativos diretosCA/SAN/senha/certificado por perna, ACL e
burstQoS0, depois corrigiu SIGTERM descoberto na imagem. Os FAIL/oráculos
inadequados e imagens intermediárias são preservados no registroC149.

Fonte final candidata9e1d011ffa22aa1225d3775b6fc99a06ae6dfc60:
208testesRustPASS, recuperação16/16 e segurança/parada13/13 locais.
CI39301735099 em execução nesta preparação; jobsRust/Ubuntu jáPASS.
PacoteCI xmqr-client0.43.0-1amd64, SHA256
`e4d09cec660a0dba20790181727b17c44040913425a3340d3838e45113241f76`,
metadados e sidecar conferidos. Não há aceite global inferido de preparação.

Os deb/sidecars publicados do broker0.43.0 e admin0.11.0 foram baixados,
conferidos e copiados para o índice local sem remover pacotes anteriores.
BrokerSHA256`c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e`,
adminSHA256`fe03ffc858e7583e7d8ce6808b4f56495c688beb69d47870db7fe0c1b8b55469`.
Nenhum pacote instalado no host, credencial restaurada ou serviço real alterado.

P236fontes/registro foram commitados emfb75667 e enviados ao GitHub. Seu
HTML local está fora dos três repositórios: só as fontes reproduzíveis e
evidências são publicadas. Tema e navegação sem seta nas folhas preservados.
A atualização final do curso/índices aguarda publicação conferida C149.

## Aceite final e reconciliação

Fase8/T02 aceita no contrato finitoP235. A revisão9e1d011 completou os seis
jobs da CI39301735099. Relatórios baixados e lidos: debugwire33PASS/1NOT_RUN,
recovery16,security13,brokers34PASS; pacote/imagemwire33PASS/1NOT_RUN,
security13 e brokers34PASS. [Matriz requisito→evidência](../../docs/phase8-acceptance.md).

[Releaseclient0.43.0/bridge0.5.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.43.0)
publicada com tag anotada61765545258a621b629728cf4e33f0cf2b92b5d3, alvo9e1d011,
seis anexos baixados iguais porSHA256 e três sidecars remotosPASS. Imagem
numerada remota confirmada por pull/run dos dois binários, digest
`sha256:9f2f798e49383332d37ac01d5ea98ce1a2056933871e86a98beb03bdd2d10ad6`.
[Registro C149](https://github.com/licodevone/xmqr-client/blob/main/prompts/registros/C149-release-0.43.0.md)
preserva falhas, revisões, cancelamentos e recusa de exportação por finais
CRLF/LF entre GitWindows/WSL. C149B normalizou apenas configuração por processo,
sem alterar fonte/histórico ou desativar gate de árvore limpa.

Plano/checklist global marcado[x] e riscado; linhaT02, matriz e README
reconciliados. Histórias C125–C139 permanecem como checkpoints anteriores.
Primeira asserção documental global confundiu uma frase histórica deC139 com
o estado vigente; P237v1.3 corrigiu o escopo da verificação, sem apagar história
ou reduzir critérios. Fase9/Windows segue planejada; certificação integral,
cluster, atomicidade distribuída e topologia que remove propriedades não
foram alegados. AdminA25fonte/CI e pacote0.11.0 continuam separados.

Índices locais atualizados e três deb/sidecars atuais conferidos, preservando
pacotes anteriores. Esses arquivos e o HTML estão fora do Git; não se alega
que foram enviados junto com as fontes do broker. Curso atualizado por updater
idempotente, sem marcar as34caixas do aluno. HTMLSHA256final
`b50b5dc9e5949d22e451a940d13f8ed36a41d0dbaf30ed4f007b46ff1ed01236`.
Validação:5unitários, estrutura207folhas/19pais,11checksChromiumPASS, cinco
capturas inspecionadas (claro/escuro desktop/mobile e impressão),444links
Markdown locais válidos e diffcheckPASS. Temas, sidebar e busca preservados.
[EvidênciaP237](../../docs/evidence/p237/reconciliation.json) e
[browser](../../docs/evidence/p237/browser.json).

Sem alterar runtime/versão broker/admin ou instalar pacotes no host do operador.
Publicação documental final faz commit/push das fontes e registros; as tags
aceitas existentes não são movidas.
