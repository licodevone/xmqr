# P192 v1 — release experimental broker/admin legado 0.34.0

Estado de entrada: `main` limpo em `95d934c`, broker/admin legado 0.33.0 publicados, estado durável v15. P183–P190 foram aceitos na árvore depois da tag 0.33.0, com CI dos commits funcionais; P191 apenas amplia o backlog futuro. Client independente 0.28.0 e admin independente 0.10.0 permanecem publicados/compatíveis.

Objetivo: publicar um marco instalável 0.34.0 do broker e `mqtt-admin` legado, reunindo os motivos MQTT 5 P183–P190. Atualizar Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING, nota de release, guias de versão/instalação e checklist. Não alterar o client ou admin independente. Fases 6A–6D, 7–9 e prioridades 10–12 continuam abertas.

Compatibilidade: documento v15 sem migração; broker 0.33.0 e admin independente 0.10.0 devem continuar lendo o estado. Preservar backup privado antes de downgrade. Retorno a broker 0.28.0 ou anterior requer backup v14 anterior à migração. Não anunciar MQTT 5 integral ou produção.

Aceite: gates Rust/fmt/Clippy/build release/licenças/distribuição, regressões P183–P190 e CI do commit exato; pacote Ubuntu 26.04 amd64 com ciclo descartável 0.33.0 → 0.34.0 → rollback, sem tocar no WSL instalado; imagens numeradas broker/admin legado executadas por digest remoto; tag anotada imutável e prerelease com anexos, tamanhos e SHA-256 remotos conferidos. Não mover Docker `latest` nem publicar repositório APT. Registrar falha e revisar o prompt antes de corrigir. Se gate essencial permanecer bloqueado, não declarar release concluída.

Revisão 2: a primeira invocação local de `cargo test --locked` (paralelismo padrão) parou na compilação da biblioteca de testes com `rustc-LLVM ERROR: IO failure on output stream: Cannot allocate memory`; portanto, a cadeia de gates não avançou. O WSL tem 7,8 GiB de RAM e 8 GiB de swap, com swap intensamente usado. Repetir `cargo test`, Clippy e builds com `-j 1`, sem mudar fonte funcional nem alegar que a primeira tentativa passou. Se a falha persistir, obter CI e evidência local alternativa antes de qualquer tag.

Revisão 3: após gates seriais PASS, a primeira invocação de `build_deb.py --skip-build` falhou no shell antes de executar Python: a interpolação de `$PATH` incluiu diretórios Windows com espaços/parênteses no argumento `bash -lc`. Repetir com PATH Linux literal mínimo (`/home/licod26/.cargo/bin:/usr/local/bin:/usr/bin:/bin`), sem mudança do empacotador nem contar a tentativa malformada como teste de pacote.
