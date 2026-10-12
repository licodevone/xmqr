# P65 rev1 — guia HTML atualizado e construção didática

Entrada broker725251b/0.11.2, client8bb7aaf/0.7.1. ArquivosDocker na raiz
preexistentes preservados e excluídos doGit. Pedido: atualizar guiaHTML e
destrinchar instalaçãoRust, criação, bibliotecas, comandos e caracteres.
Escopo: gerador versionado do guia/conteúdo didático, docs/code-guide.html,
README e registroP65. Sem runtime/manifests/versão/serviços reais.
Regerar catálogo completo de prompts/registros e linhas das fontes atuais,
preservando notas assistidas e distinção de análise humana. Acrescentar percurso
didático explícito (não cronologia inventada): preparação Ubuntu/Windows,
Cargo+projetoHello mínimo verificável, módulos, TCP/codec/QoS/store/auth/TLS,
clientrumqttc, testes, systemd/deb/Docker/release. Explicar cada dependência
direta e features/constraints do manifest com evidência de usos no código.
Glossário de tokens/caracteres por contextoRust/TOML/Bash/PowerShell, comandos
decompostos e leituras humanas profundas dos fluxos; exemplosnão são produção.
Fontes primáriasRust/Cargo/SDK para detalhes técnicos; limites de compatibilidade
claros. Scripts/arquivos de apoio catalogados, sem prometer semântica individual
completa de todas as linhas. Validar fontes numeradas idênticas, links/HTML/JS,
exemplos mínimos emtemporário e renderização quando disponível. Falhas: revisar
prompt antes de corrigir. Commit/push autorizados; sem tag/release documental.

## Rev2 — revisão e correções antes da entrega

Gerador histórico continha P55 como PREPARED e resumo genérico C36/C37.
Revisar segundo os contratos atuais, preservar os documentos originais como
histórico e descrever startup síncrono P64. Conferir unidade de cada quota
contra store/router, não presumir total versus por sessão. Falha inicial de
aplicação de patch por contexto textual: nenhum arquivo foi alterado por esse
patch; aplicar agora com contexto real. Executar eco TCP em temporário, conferir
igualdade de fontes/notas, navegação interna e render desktop/mobile.

## Rev3 — ambiente da verificação

A primeira execução do verificador diretamente por wsl/python não encontrou
Cargo no PATH. Falha de preparação do verificador, não de compilação dos
exemplos. Executar a validação pelo shell Bash de login já confirmado com
Cargo1.99.0, sem instalar ferramentas nem mudar variáveis globais. Registrar
esse resultado antes de repetir os exemplos.

## Rev4 — apresentação mobile

Exemplos Cargo/eco TCP e igualdade das12492 fontes passaram. Busca/recolhimento
funcionam em Edge headless. A verificação mobile detectou largura excedente;
ajustar quebra de nomes longos e contêineres de tabela, repetir apenas render
e integridade documental. Não repetir gates de runtime sem mudança funcional.
