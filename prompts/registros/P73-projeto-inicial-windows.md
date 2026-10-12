# P73 — primeira base didática Windows

Data2026-10-12. Base Git17a4d10; árvore inicialmente contém P68 eanexos Docker,
preservados. PromptP73 preparado antes de criar código, P00/contexto eP03/
recorte didático criados antes dos executáveis.

Histórico: P03 pede bootstrap; P00 é contexto. O primeiro commit da origem
be28274 já declara0.2.0 e o primeiro XMQR f7efe35 já declara0.3.0. Não é possível
atribuir seus arquivos como saída exata isoladaP03. Nova base didática separada
emcurso/projeto-inicial: dois pacotes/std, comentáriosP03, manifests/locks,
README com palavras/caracteres/comandos e licença. Nenhuma fonte do broker ou
client atual alterada; sem listener/protocoloMQTT nessa primeira etapa.

PASS Windows nativo Rust/Cargo1.98.1 MSVC: generate-lockfile offline, fmtcheck,
cargo test (0 testes, não evidência MQTT), Clippyall-targets -Dwarnings ebuild
release para ambos. Execuções reais imprimiram as mensagens esperadas eexit0.
Builds emCARGO_TARGET_DIR temporário, somente nos processos de validação;
nenhuma alteração de toolchainglobal/serviço/firewall/WSL/Docker.

ZIP/guia/proveniência locais em../docs/curso-udemy/projeto-inicial, gerados por
scripts/build_initial_project.py. PASS: ZIP íntegro ecompilação/execução
Windows após extração emdiretório temporário, com mesma saídaesperada.
Fonte/gerador serão commitados/sincronizados conforme autorização da conversa.
Sem tag/release do broker/client atuais; P01 ou fatias seguintes não executadas.
