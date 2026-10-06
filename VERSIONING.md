# Versionamento

O código deste snapshot identifica a versão `0.5.0` em `Cargo.toml` e
`Cargo.lock`. Uma versão publicada deve receber a tag anotada correspondente,
`v0.5.0`, somente depois de passar pelos gates de release. A versão 0.5.0
está preparada localmente; não foi criada tag ou release nesta etapa.

Para cada incremento futuro:

1. Implemente e teste a mudança; registre recursos, limitações e migração no
   `CHANGELOG.md` e nos documentos relevantes.
2. Atualize `Cargo.toml` e `Cargo.lock` para a mesma versão.
3. Confira o diff e os arquivos preparados; nunca registre certificados,
   chaves privadas, senhas, dados de execução ou diretórios gerados.
4. Faça um commit da versão e crie uma tag anotada `vMAJOR.MINOR.PATCH` apenas
   depois das verificações correspondentes.

Enquanto faltarem os gates de conformidade e operação, use a série `0.x`.
`1.0.0` exige evidências de conformidade, interoperabilidade, recuperação,
segurança e operação. Até lá, os arquivos apenas estão preparados localmente.
