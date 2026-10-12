# P69 rev1 — expansão sincronizada da sidebar e do corpo

Entrada58b6cd6. Usuário retomou após aguarde para sincronizar abrir/fechar em
ambos os lugares. P68 de capítulosIA permanece preparado, sem execução dessa
fatia. HTML foi movido pelo usuário para ../docs/code-guide.html; preservar
destino e anexos Docker existentes. Nenhuma alteração ao broker/client.

Corrigir o controle de expansão da lista de subtópicos, que era independente
do painel principal apesar dos links já atualizarem aria-expanded. Cada tópico
da sidebar deve ser details vinculado ao details do corpo, sincronizando estado
nativo nos dois sentidos. Abrir subtópico revela ancestrais; fechar pai reflete
estado efetivo dos filhos. Categorias somente organizam a navegação, sem criar
um segundo controle contraditório. Manter âncoras/hash/busca/mobile.
Atender pedido anterior de links Abrir todos os tópicos emsidebar ecorpo.
Atualizar gerador/notas para destino compartilhado, sem recriar HTML antigo.
README aponta para destino local; informar que arquivo agregado está foraGit
do broker, mas gerador/conteúdo são versionados. Não inicializarGit noagregador.

Aceite: testes reais de details.sidebar↔details.corpo, links individuais,
filhos/ancestrais, abrir/fechar todos, hash, busca, Escape/mobile/desktop;
fontes12492/27 idênticas, IDs/âncoras válidas, diff limpo. Revisar prompt antes
de corrigir erros. Commit/push autorizado; sem release/tag documental.
