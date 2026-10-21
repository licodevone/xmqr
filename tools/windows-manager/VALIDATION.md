# P239 - validação local do gerenciador

Ambiente: Windows x86_64, Rust 1.99.1, PowerShell; execução sem instalação,
sem escrita no inventário HKLM e sem iniciar/parar serviço do operador.

| Checagem real | Resultado |
| --- | --- |
| cargo fetch inicial | BLOCKED: DNS de crates.io indisponível |
| cargo generate-lockfile --offline, dependências locais revisadas | PASS |
| cargo check --locked --offline | PASS |
| cargo test --locked --offline, tentativa inicial | 8 PASS / 1 FAIL: [] no PowerShell 5.1 |
| Revisão v1.3 antes da correção e repetição de cargo test | 9/9 PASS |
| cargo clippy --locked --offline --all-targets -- -D warnings | PASS |
| cargo fmt --all -- --check | PASS |
| cargo build --locked --offline | PASS |
| Debug --diagnose, stdout capturado por subprocesso Python | PASS: exit 0, JSON components=[] e error=null |
| Coleta de licenças Windows por Cargo metadata offline | PASS: 79 dependências com textos de licença |
| Consulta CIM de serviço fictício ausente | Consulta indisponível neste ambiente; estado Unknown retornado corretamente |
| Serviço real, UAC, Explorer/editor, visualização da bandeja, reboot/login e ciclo MSI | NOT_RUN; requer ambiente de homologação |

Os nove testes cobrem todas as oito combinações de presença dos três produtos,
agregação de estados, recusa de IDs/serviços/caminhos/URLs inválidos, ações por
estado, campos opcionais inválidos, dados Unicode tratados como dados (incluindo
texto que seria código se interpolado), deadline do subprocesso e consulta vazia
sem mutação. Não substituem a prova de serviços instalados em VM.

Houve aviso do compilador sobre hard links indisponíveis no cache incremental,
com cópia de arquivos como fallback; código de saída dos gates finais foi zero.
O bloqueio DNS motivou a revisão v1.1, sem contornar restrições de rede.
As revisões preventivas e a falha inicial estão em P239-tray-revisions.md.

Build release e MSI são executados pela frente de empacotamento, com registro
agregado P239 no repositório. Esta evidência não afirma homologação de broker,
client ou admin nativos nem validação de persistência/ACL Windows desses produtos.
