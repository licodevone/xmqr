# P79 — aula inicial, navegação e apresentação

Data: 2026-10-13. Base e8bd06b. Prompt preparado antes da implementação,
com revisões 2–5 antes das correções de fonte, conectores, ambiente do finalizador
e captura mobile.
Pedido autoriza materiais do curso, HTML, apresentação, commit e sincronização.

## Entrega

- Título do HTML: Da lógica ao Broker e Clientes MQTT utilizando Rust.
- Botões globais alternam Abrir/Fechar todos os tópicos, sincronizando sidebar
  e corpo. Links Ir ao tópico/Ir à aula com contraste, foco e aparência de botão.
- Seção 0, aula inicial e briefing: OCaml, Graydon Hoare, Mozilla, rustc,
  representações internas, LLVM, C/GCC/Clang, vantagens/desafios e limites.
- Três diagramas HTML e diagramas editáveis de compilação e arquitetura nos slides.
- 35 slides com seção e aula: aula inicial, cinco seções, 16 aulas práticas
  e encerramento. Fala sugerida e orientação privada em todos os slides do professor.
- PPTX aluno sem notas privadas, PPTX professor com notas, roteiro privado HTML.
- Fontes e finais em curso/reconstrucao-primeiro-commit, geradores em scripts.
  Artefatos locais em ../docs/curso-udemy/primeiro-commit, pacote completo atualizado.

## Evidência real

PASS: verify_first_commit_guide.py confere 6098 linhas Rust contra os snapshots,
links/âncoras, R10 exato ao primeiro commit e CRC de onze ZIPs. ZIP completo contém
guia atualizado e apresentações. Dez ZIPs de código preservados.

PASS: Edge/Playwright em desktop 1440x1000 e mobile 390x844: título, abrir/fechar
individual nos dois sentidos, global nos dois controles, âncora, busca por linha,
três diagramas HTML, nenhum erro JavaScript. Screenshots em target/p79-apresentacao.

PASS: finalizador das duas apresentações, integridade de pacote, layout e fontes
Arial/Consolas, reimportação first-party. 35 slides renderizados e inspecionados
individualmente. Renderização reimportada do PPTX final comparada pixel a pixel:
35 imagens idênticas às aprovadas. XML visual dos 35 slides igual nas duas versões.
Notas do professor verificadas em todos os slides; versão dos alunos sem texto privado.

Resumo e SHA-256: docs/results/p79-course-slides-summary.json. Recibos completos,
previews e browser-qa.json ficam em target/p79-apresentacao. Não abriu PowerPoint
nativo; não reivindicar inspeção nele. Nenhum teste Rust repetido por alteração
de texto/UI que preserva fonte histórica.

## Correções e limites

Primeiro draft usou propriedade de fonte não reconhecida e exportou Aptos:
finalizador recusou; corrigido com typeface e tema. Setas apontavam à origem:
revisão visual corrigiu destino. Reimportação exigia variável do runtime e
recibo separado da pasta final: corrigidos apenas no processo/diretórios de QA.
Rótulo MIR ajustado para evitar quebra de palavra. Revisões documentadas no prompt.

Garantias didáticas qualificadas: Rust seguro não elimina vazamentos, deadlocks
ou todo overflow, e unsafe não desliga borrow checker. LLVM é backend padrão.
Sem números comparativos de desempenho ou tempos de build não medidos.

Outras alterações no workspace (P78/distribuição/runtime) surgiram durante o
trabalho e foram preservadas fora do staging desta entrega. Client não alterado.
Sem versão/tag/release do produto por mudanças no curso.
