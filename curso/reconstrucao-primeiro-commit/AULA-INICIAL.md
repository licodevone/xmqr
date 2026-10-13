# Da lógica ao Broker e Clientes MQTT utilizando Rust

## Seção 0 — Rust, C e o caminho até o executável

### Aula inicial — Origem, compilação e escolhas da linguagem

Ao terminar esta aula você conseguirá distinguir linguagem, compilador e
gerenciador de projetos; acompanhar o caminho do arquivo de texto até o
executável; explicar por que Rust ajuda a construir nosso broker e quais
responsabilidades continuam com quem programa.

**Briefing da aula:** Rust começou como projeto pessoal de Graydon Hoare em
2006, enquanto ele trabalhava na Mozilla. O primeiro compilador foi escrito em
OCaml, uma outra linguagem de programação. A Mozilla passou a financiar o
projeto em 2009. Hoje o compilador oficial é escrito em Rust e usa LLVM como
backend padrão. Isso permite combinar regras próprias de tipos e memória
com uma infraestrutura de otimização e geração de código para diferentes
processadores. No curso, vamos escrever Rust e usar Cargo para organizar
bibliotecas, compilar e testar um broker e seus clientes MQTT.

### 1. Linguagem, compilador e Cargo

A linguagem define a sintaxe e o significado do programa. O arquivo `.rs`
contém texto que você pode editar. O compilador `rustc` verifica e transforma
esse texto. Cargo coordena o projeto: lê `Cargo.toml`, resolve dependências,
aciona `rustc` e organiza comandos como `cargo build`, `cargo run` e `cargo test`.
Biblioteca é código reutilizável; em Rust uma unidade de distribuição se chama
crate. O compilador também compila as dependências necessárias.

OCaml não é um requisito de instalação para o aluno. Ele faz parte da história
do primeiro compilador. Um compilador escrito na própria linguagem é chamado
de auto-hospedado: versões anteriores ajudam a compilar a próxima versão.

### 2. Como o rustc compila

O desenho simplifica etapas internas, sem representar todas as consultas e passes:

1. **Texto e análise:** o compilador reconhece palavras e símbolos e monta uma
   estrutura que representa o programa. AST significa árvore de sintaxe abstrata.
2. **Representações Rust:** HIR é uma representação de alto nível. O compilador
   resolve nomes e verifica tipos. MIR é uma representação intermediária de
   nível médio usada, entre outras análises, pela verificação de empréstimos.
3. **LLVM IR:** o backend padrão transforma a representação Rust em instruções
   intermediárias que o LLVM entende. IR significa representação intermediária.
4. **Otimização e geração:** passes analisam e transformam o IR, respeitando
   suas regras. O gerador produz instruções para o alvo, como x86-64 ou AArch64.
5. **Linkedição:** o linker combina arquivos objeto e bibliotecas necessários
   para formar o executável, como um `.exe` no Windows.

Compilar não significa executar. A execução começa quando o sistema operacional
carrega o executável. O executável depende de arquitetura e sistema operacional:
um `.exe` Windows não se torna um binário Linux apenas por mudar a extensão.

### 3. Como o LLVM funciona

**Front-end:** a parte específica de cada linguagem entende suas regras e
produz uma representação aceita pelo LLVM. Rust faz análises próprias antes
desse ponto. Clang é um front-end para C e C++, entre outras linguagens.

**Otimizador:** aplica passes ao IR, por exemplo simplificar uma expressão ou
remover trabalho sem efeito observável. Linguagens diferentes podem reutilizar
passes, desde que expressem corretamente suas regras no IR. O conjunto depende
do pipeline e das opções de compilação. Não há promessa de otimização máxima
nem de “centenas” de passes executados em todo programa.

**Back-end:** traduz o IR para instruções do alvo. Intel e AMD são fabricantes;
x86-64 é uma arquitetura utilizada por ambos. ARM é uma família de arquiteturas,
incluindo AArch64. O alvo também envolve sistema operacional e convenções de
chamada. LLVM não é uma máquina virtual obrigatória que o usuário instala para
executar nosso broker. Rust possui outros backends em desenvolvimento; esta aula
explica o backend padrão LLVM.

### 4. Como C compila e o que mudou com Rust

No fluxo tradicional do GCC para C, o pré-processador trata `#include` e macros,
o compilador produz assembly, o assembler produz arquivos objeto e o linker
forma o executável. As ferramentas podem integrar essas etapas num só comando.
C também pode usar Clang e LLVM. Portanto, usar LLVM não é exclusividade do Rust
e C continua sendo uma linguagem atual.

Exemplos para observar as etapas em um ambiente com GCC instalado:

```sh
gcc -E exemplo.c -o exemplo.i
gcc -S exemplo.c -o exemplo.s
gcc -c exemplo.c -o exemplo.o
gcc exemplo.o -o exemplo
```

`-E` interrompe após pré-processamento; `-S` gera assembly; `-c` gera objeto sem
linkar; `-o` escolhe o nome de saída. Esses comandos ilustram C e não criam uma
dependência GCC para seguir o curso Windows/MSVC. Não vamos instalar GCC nesta aula.

### 5. Vantagens e desafios das duas linguagens

| Aspecto | Rust | C |
| --- | --- | --- |
| Memória | Ownership e empréstimos limitam referências inválidas no código seguro. | Alocação dinâmica exige gerenciar duração e liberação, como malloc/free. |
| Concorrência | Tipos e regras de acesso ajudam a impedir data races no código seguro. | Quem programa deve garantir sincronização e duração dos dados compartilhados. |
| Ferramentas | Cargo integra dependências, builds e testes. | Há ecossistemas consolidados como Make/CMake e gerenciadores externos. |
| Aprendizagem | Ownership, lifetimes e traits exigem prática e leitura dos diagnósticos. | Sintaxe central menor, mas ponteiros e comportamento indefinido exigem cuidado. |
| Compilação | Dependências, generics e otimizações podem aumentar o trabalho do compilador. | Projetos pequenos podem compilar rapidamente; tamanho e opções também influenciam. |
| Hardware | Há Rust embarcado e no_std; é preciso confirmar suporte ao alvo e às bibliotecas. | Amplo histórico de toolchains para dispositivos e integração com APIs existentes. |
| Desempenho | Pode gerar código nativo eficiente sem coletor de lixo obrigatório. | Pode gerar código nativo eficiente com controle direto de recursos. |
| Legado | FFI permite integração, com contratos que precisam ser respeitados. | APIs e ABI C são amplamente utilizadas por sistemas existentes. |

### 6. Segurança sem promessas absolutas

Ownership significa propriedade: um valor tem um responsável por sua duração.
Borrowing significa empréstimo: uma referência acessa um valor sem receber sua
propriedade. O borrow checker verifica se esses acessos respeitam duração e
exclusividade. Não se trata de um coletor de lixo que procura objetos inutilizados
periodicamente. Recursos de valores como `String` são normalmente liberados
quando seu responsável sai de escopo.

Rust seguro evita problemas como uso após liberação e data races, sob as
garantias da linguagem e de suas abstrações. Data race é acesso concorrente
conflitante à mesma memória sem sincronização adequada, com pelo menos uma
escrita. Isso não elimina qualquer erro de concorrência: deadlocks e erros
na ordem de tarefas continuam possíveis.

Acesso fora dos limites de um vetor pode ser detectado durante a execução e
causar panic. Isso protege a memória, mas não garante continuidade do serviço.
Overflow numérico é outro assunto: o resultado depende da operação e das opções
de checagem; existem operações explícitas checked, wrapping e saturating.
Vazamentos de memória também são possíveis em Rust seguro. Por isso, não vamos
afirmar que o compilador elimina todos os overflows e vazamentos.

`unsafe` permite determinadas operações cujo contrato o programador precisa
verificar, como chamar certas funções externas ou acessar ponteiros brutos.
Ele não desliga o borrow checker nem todas as outras verificações. Usar uma
biblioteca com interface segura pode encapsular a interação com C. O código do
XMQR segue as regras do projeto que proíbem acrescentar código unsafe próprio.

### 7. Ligação com o projeto MQTT

Nosso broker recebe bytes da rede, valida pacotes, controla sessões, autentica
clientes e guarda estado. Rust ajuda a estruturar esses recursos com tipos e
regras de duração. Ainda precisamos implementar corretamente MQTT, limitar
filas e memória, validar credenciais e testar recuperação. Compilar com sucesso
é uma etapa, não uma prova de ausência de bugs ou de equivalência ao Mosquitto.

A sequência prática continua na Seção 1, Aula 1, com instalação/verificação das
ferramentas e criação de um pacote vazio. As etapas R01 a R10 preservam o código
acumulado até reconstruir os 35 arquivos do primeiro commit histórico.

### Fontes primárias para aprofundar

- [Arquivo histórico publicado por Graydon Hoare](https://github.com/graydon/rust-prehistory)
- [História e vínculo com a Mozilla](https://blog.rust-lang.org/2020/08/18/laying-the-foundation-for-rusts-future.html)
- [Visão geral do compilador Rust](https://rustc-dev-guide.rust-lang.org/overview.html)
- [Geração de código Rust](https://rustc-dev-guide.rust-lang.org/backend/codegen.html)
- [Representação LLVM IR](https://llvm.org/docs/LangRef.html)
- [Gerador de código LLVM](https://llvm.org/docs/CodeGenerator.html)
- [Etapas do GCC](https://gcc.gnu.org/onlinedocs/gcc/Overall-Options.html)
- [Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- [Vazamentos em Rust seguro](https://doc.rust-lang.org/nomicon/leaking.html)
- [Significado de unsafe](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html)
- [Overflow numérico](https://doc.rust-lang.org/reference/expressions/operator-expr.html#overflow)
- [Rust embarcado e no_std](https://doc.rust-lang.org/embedded-book/intro/no-std.html)
