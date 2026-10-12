# P77 rev1 — reconstrução guiada do primeiro commit XMQR

Pedido: passo a passo até finalizar a criação do primeiro commit do XMQR,
mantendo os requisitos de curso: digitação, comandos/bibliotecas explicados,
etapas cumulativas, prompts preparados antes, artefatosHTML e ZIP.

Entrada: HEAD90a46fa limpo, primeiro commit
f7efe357cdcd4a05e922a5fb205bd8757cdc5625, versão0.3.0,35 arquivos e6083 linhasRust.
Já contém mqtt-broker, mqtt-client e mqtt-admin; não é HelloWorld nem cliente
independente. Não há prompts versionados no primeiro commit. Não inventar
autoria/ordem histórica anterior; a sequênciaR01..R10 será reconstrução didática
nova P77, cujo resultado final tem os mesmos35 arquivos do commitf7efe35.

Escopo: curso/reconstrucao-primeiro-commit com roteiro detalhado e dez prompts
R01..R10; scripts/build_first_commit_course.py para artefatos/validação.
R01 package inicial/main de apresentação; R02 Cargo.toml/lock históricos;
R03 persistência+ator; R04 autenticação/ACL; R05 transporteTCP/TLS;
R06 quatro arquivosMQTT e lib final; R07 main real do broker; R08 admin;
R09 client com cinco arquivos; R10 demais docs/configs/exemplo, fonte final exata.
Preservar tudo já acrescentado; substituir apenas lib/main/manifests pedagógicos
necessários, com diff e proveniência. Não atribuir todos os trechos a um único
prompt antigo. Originais intactos em codigo/; comentários didáticos em guias.

Roteiro do zero: verificar Rust/Git instalados, como instalar quando ausentes
(só instruções, não executar instalações), cargo new --vcs none, árvore de
pastas, ordem de digitação, conteúdo integral de arquivos e papel de cada
biblioteca/feature/símbolo novo, compilação a cada etapa, fixar Cargo.lock,
validação final e git init/add/commit local do aluno. Commit do aluno terá outro
SHA por metadados; conteúdo equivalente não recria automaticamente SHA antigo.
Não iniciar/pushar um novo repo ou sobrescrever o XMQR existente do usuário.

HTML com sidebar e tópicos synchronized details, abrir/recolher todos, âncoras,
busca por arquivo/linha; listar todoRust e demais fontes. Explicações assistidas
de sintaxe por linha são ajuda de leitura, não auditoria semântica humana integral;
incluir narrativa específica de cada módulo/função e fluxo MQTT real.
Cargo.lock é artefato gerado, preservar fornecido em vez de digitar seus hashes.
Não executar exemplo minimal_mqtt: bindLAN histórico não é laboratórioloopback.
Histórico não tinha LICENSE; informar isso sem acrescentar arquivo ao código
final que se afirma idêntico ao primeiro commit. License foi commit posterior.

Artefatos locais ../docs/curso-udemy/primeiro-commit: índiceHTML, guiaMarkdown,
dez ZIPs cumulativos, pacote completo e hashes. Cada ZIP contém instruções,
prompt correspondente, diff/manifesto, código completo daquele estágio.

Validação: hashes/blobs Git e igualdade final dos35 arquivos; compilação/check
de cada etapaWindowsRust1.98.1 eUbuntu26WSL/Rust1.99 com targets isolados; na
fonte final, fmt/test/clippyLinux em cópia isolada para registrar limitações reais.
Se instruir pub/subloopback, ensaio isolado com novo estado e porta dedicada,
somente processos do laboratório da tarefa; não modificar serviço/firewall/TLS
ou credenciais reais. Não anunciar TLS/Mosquitto/MQTT5 como validados.
Revisar prompt antes de corrigir erros, preservar snapshot histórico mesmo se
gates dequalidade antigos falharem. Registrar logs/reprodução/resultados atuais.
Commit/push do material autorizado; sem tag/release nova do produto.

## Rev2 — qualidade histórica e ajuste opcional separado

Dez etapas build/check PASS em Windows/Ubuntu;52 testesLinux e pub/sub PASS.
Clippy1.99 -Dwarnings falhou por assert_is_empty em src/mqtt/store.rs:305:
debug_assert!(remainder.is_empty()). Não alterar R10 nem sua igualdade Git.
Explicar a falha e validar debug_assert_eq!(remainder, []) em cópia adicional
isolada, com fmt/test/clippy, antes de recomendar como correção posterior.
Registrar diff e evidência fora do código histórico. Prompt R10rev2 esclarece
que gate dequalidade novo pode reprovar snapshot antigo que ainda compila.

## Rev3 — estado de exercício fora da pasta Git e prompts preservados

Revisão do roteiro detectou estado de aula dentro do projeto: o marcador de
perfil não é coberto integralmente pelo.gitignore original e poderia entrar no
primeiro commit. Mudar instruções para $HOME/.local/share/xmqr-curso-r10, fora
da pasta codigo/projeto, e explicar variávelHOME. Ensaios já usam estado externo
à fonte e mantiveram árvoreGit exata. Tornar explícita criação do.gitignoreR01.
--prepare deve preservar prompts existentes, incluindo revisãoR10, para não
sobrescrever edições do professor numa regeneração. Reexportar artefatos e
verificar links, UI e hashes; não repetir compilação de fontes inalteradas.

## Rev4 — instruções de instalação opcionais com contexto correto

Duas tentativas de patch para detalhar instalaçãoWindows foram recusadas por
contextos extras incorretos; nenhum arquivo alterado. Reaplicar somente na
âncora real dos pré-requisitos, sem hunk extra, e fornecer comandos rustup/Linux
oficiais como instruções ao aluno. Não executar instalações. Regenerar guia e
conferir fidelidade/links, mantendo os resultados de compilação já executados.
