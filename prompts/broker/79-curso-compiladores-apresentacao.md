# P79 rev1 — aula inicial, navegação e apresentação do curso

Data: 2026-10-13. Entrada: HEAD e8bd06b, guia P77 e checkpoints R01–R10.
Existe prompt P78 não rastreado de outro escopo: preservar e não incluir no commit.
Manifest atual 0.11.3 não é a versão histórica 0.3.0 ensinada nesta reconstrução.

Objetivo autorizado: atualizar o HTML do primeiro commit com o título
“Da lógica ao Broker e Clientes MQTT utilizando Rust”, melhorar visualmente
“Ir ao tópico”/“Ir à aula”, sincronizar abrir/fechar todos os tópicos e criar
apresentação editável com seções, aulas e notas privadas em cada slide.

Preparar primeiro a Seção 0 / Aula inicial: origem do compilador em OCaml,
Graydon Hoare e apoio posterior da Mozilla, rustc e LLVM, front-end,
representações intermediárias, otimização, geração de código e linker.
Comparar pipeline C/GCC e C/Clang, vantagens e desafios Rust/C com ilustrações.
Usar fontes primárias. LLVM é backend padrão, não única possibilidade.
Rust seguro evita acesso inválido à memória e data races nas garantias da
linguagem, mas não elimina vazamentos, deadlocks ou todo overflow. Bounds
checks podem ocorrer em execução. unsafe não desliga borrow checker.
Tempo de compilação e suporte de hardware dependem de alvo/projeto/ferramentas.

Escopo: material em curso/reconstrucao-primeiro-commit, gerador HTML,
novo gerador de apresentação, execução registrada em prompts/registros.
Artefatos em ../docs/curso-udemy/primeiro-commit; previews/QA em target/p79.
Preservar numeração das 16 aulas anteriores e código histórico/ZIPs R01–R10.
PPTX professor contém fala sugerida e orientação privada somente nas notas;
versão para alunos remove notas privadas. Guia privado separado descreve cada slide.
Slides legíveis, passos concretos, bibliotecas/comandos contextualizados,
sem analogias escolares ou textos de preparação de aula na tela dos alunos.

Aceite: aula inicial primeiro conteúdo de ensino; briefing acessível no HTML;
título fiel; botões com foco de teclado e contraste; abrir/recolher mantém sidebar
e corpo sincronizados. Todas as seções/aulas cobertas pelos slides e cada slide
do professor tem notas de fala e orientação. Diagramas editáveis e fontes
rastreáveis. ZIP completo e hashes regenerados; fontes históricas idênticas.

Validação proporcional: integridade/links/código do guia, navegação em browser
desktop/mobile, abrir/fechar individual e global, ausência de erros JS, PPTX
estrutural e renderização de todos os slides para inspeção visual. Sem repetir
compilação Rust de código inalterado. Revisar este prompt antes de corrigir falhas.
Commit/push autorizados no histórico da conversa. Sem release/tag do runtime
por alteração didática, sem modificar client, serviços, certificados ou credenciais.

## Rev2 — fonte exportada e direção dos conectores

O primeiro rascunho renderizou 35 slides, mas o finalizador recusou a fonte
exportada Aptos em vez das fontes Arial/Consolas escolhidas. Consultar o campo
de fonte documentado e definir também o tema, sem relaxar a verificação.
A revisão visual mostrou pontas de setas voltadas à origem: ajustar conectores
para indicar o destino. Evitar quebra no meio de “pré-processador” no fluxo C.
Exportar outro rascunho, renderizar novamente e repetir o aceite estrutural.

## Rev3 — ambiente do validador e comando Windows

Fontes e layout foram aceitos, mas a reimportação do rascunho exige variável
RUNTIME_NODE_MODULES para localizar o runtime empacotado. Definir caminho apenas
no processo do gerador, sem instalar bibliotecas ou mudar ambiente global.
No slide R01 retirar a continuação Linux do comando cargo new: mostrar o
comando em uma linha lógica, permitindo apenas quebra visual automática.

## Rev4 — diretório de entrega e rótulo MIR

A reimportação passou, mas o finalizador exige recibo de validação fora da
pasta final. Usar target/p79-entrega como destino privado validado, separado
de target/p79-apresentacao, depois copiar o PPTX aceito aos artefatos do curso.
A renderização revelou quebra no meio de Empréstimos: usar rótulo MIR / Borrow /
checker com quebras explícitas, mantendo a explicação em português nas notas.

## Rev5 — captura mobile e rastreamento das entregas

Controle mobile passou, mas foco prévio no campo de busca deslocou a captura
para o corpo após redimensionar. Reabrir o guia no viewport mobile e remover
foco antes de capturar, conferindo a posição do botão dentro da tela.
Versionar também as duas apresentações finais e roteiro de fala para que o
commit contenha entregas editáveis. Gerador preserva cópias nos artefatos locais.
