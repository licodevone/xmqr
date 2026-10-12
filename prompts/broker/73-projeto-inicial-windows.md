# P73 rev1 — base inicial didática para Rust nativo Windows

Entrada: HEAD confirmado antes de editar; broker0.11.2/client0.7.1.
Usuário pediu projeto inicial, perguntou qual prompt descreve a primeira
criação e exige execução com Rust instalado noWindows. Rust local confirmado:
cargo/rustc1.98.1, stable-x86_64-pc-windows-msvc.

Verificação histórica: P03 solicita bootstrap; P00 descreve contexto. Git da
origem começa com be28274/0.2.0 eXMQR com f7efe35/0.3.0. Não existe snapshot
separado comprovado da execução originalP03. Criar implementação didática nova,
identificada explicitamente, sem apresentá-la como recuperação do código antigo.

Escopo: curso/projeto-inicial com promptP00/contexto eP03/recorte inicial,
dois pacotes Rust independentes (broker/client), Cargo.toml/lock/main.rs,
README detalhado, explicação HTML/ZIP local e registro. Código desta primeira
etapa imprime identificação e encerra; não promete listener ou protocoloMQTT.
Sem dependências externas, Tokio, TLS, estado ou serviço neste recorte.
P03 histórico permanece inalterado; instruções mais amplas ficam fora deste
primeiro recorte, identificadas no promptdidático. Não criar workspace no
broker principal ou alterar fontes/manifests atuais. Anexos preexistentes intactos.

Escrever comentários de origem P03 só nos arquivos didáticos. Explicar cada
arquivo, linha, token e comando, mantendo P00 como preparação antes doP03.
Usar PowerShell/cargo locais: gerar lockoffline, fmt, build, clippy e execução
dos dois binários; test conforme gates, com0 testes explicitado sem inventar
cobertura. Validar ZIP porextração temporária e execuçãoWindows a partir dele.
Artefatos foraGit em ../docs/curso-udemy/projeto-inicial; links no índice existente.
Fonte egerador versionados; nenhuma instalação/toolchainglobal/serviço alterados.
Revisar prompt antes de corrigir erro. Commit/push previamente autorizados;
sem tag/release de broker ou client reais nesta etapa didática.
