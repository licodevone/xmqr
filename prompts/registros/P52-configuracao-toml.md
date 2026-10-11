# P52 — configuração TOML

Base: main 8e55f80, broker 0.10.0. Prompt P52 rev1 criado e apresentado antes
do código; rev2 antes dos ajustes de clippy e rev3 antes da normalização de docs.

Implementado MQTT_CONFIG, version=1 obrigatório, esquema tipado estrito,
leitura limitada a 64 KiB, caminhos relativos ao arquivo e overrides MQTT_*.
Ambiente global não é modificado. TLS/autorização são carregados antes de criar
o marcador de perfil. Configuração inválida não cria estado nos casos testados.
Documentação e exemplo adicionados, sem alterar instalações reais.

Primeira tentativa: 89 testes passaram; clippy recusou must_use ausente e cast
u64/usize no teste. Após revisão do prompt, atributo e conversão verificada
corrigidos. Diff check encontrou finais vazios nos documentos; rev3 registrada
antes de normalizar os arquivos.

Validação final em Ubuntu-26.04/WSL: fmt, 89 testes, clippy com -D warnings e
build dos binários aprovados. C27: 4 testes; shutdown: 3; Last Will: 9, todos
aprovados. Testes usam processos e diretórios temporários. Cliente sem alterações.

Decisão: manter versão 0.10.0 e changelog não lançado. Sem tag/release nesta
etapa: pacote publicado não inclui P52; preparar próximo marco e validar pacote
antes de anunciar nova versão. Próxima etapa: prompt para limites configuráveis,
com coerência entre transporte, sessões e estado durável, antes da implementação.
