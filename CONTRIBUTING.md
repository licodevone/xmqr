# Contribuindo com o XMQR

Obrigado por ajudar a evoluir o XMQR. O projeto prioriza correção de protocolo,
limites explícitos e evidências reproduzíveis acima de quantidade de recursos.

## Antes de começar

1. Pesquise issues e pull requests existentes.
2. Para mudanças grandes, abra uma discussão ou issue descrevendo o problema,
   o comportamento MQTT esperado e o recorte inicial.
3. Não inclua certificados, chaves, senhas, arquivos de estado ou dados reais.
4. Baseie requisitos MQTT nas especificações OASIS e registre a cláusula nos
   testes de conformidade quando aplicável.

## Preparar o ambiente

```bash
git clone https://github.com/licodevone/xmqr.git
cd xmqr
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-target"
cargo build --locked --all-targets
```

Use Rust estável compatível com `rust-version` do `Cargo.toml`.

## Fluxo de contribuição

1. Crie uma branch a partir de `main`.
2. Implemente uma fatia vertical pequena e executável.
3. Adicione testes determinísticos.
4. Atualize documentação, matriz de conformidade, ADR e migração quando forem
   afetados.
5. Execute os gates locais.
6. Abra uma pull request explicando riscos, limites e evidências.

## Gates obrigatórios

```bash
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Mudanças no wire format, persistência, autenticação ou ACL precisam de testes
negativos. Alterações que cruzam componentes precisam de teste de integração ou
interoperabilidade.

## Regras de arquitetura

- Separe codec, conexão, sessão, roteamento, persistência, segurança e
  transporte.
- Não bloqueie o hot path assíncrono com locks bloqueantes, callbacks ou I/O de
  disco.
- Preserve ordenação por publicador e semântica QoS.
- Não confirme persistência antes do nível de durabilidade configurado.
- Represente estados válidos com tipos, evitando combinações booleanas frágeis.
- Mantenha limites para pacotes, conexões, inflight, filas, tópicos e payloads.
- Nunca exponha segredos ou payloads em erros e logs.

## Commits e versões

Use mensagens curtas no imperativo, preferencialmente no formato Conventional
Commits, por exemplo:

```text
feat(router): adicionar índice limitado de assinaturas
fix(qos2): persistir PUBREL antes do PUBCOMP
docs(security): explicar rotação de certificados
```

Não altere a versão em uma pull request comum. O mantenedor prepara commits de
release, atualiza `CHANGELOG.md`, cria a tag `vX.Y.Z` e publica a release.

## Pull requests

Uma PR deve informar:

- problema e escopo;
- cláusulas MQTT afetadas;
- impacto em compatibilidade e persistência;
- estratégia de backpressure e novos limites;
- testes executados;
- riscos ou trabalho futuro conhecido.

Ao contribuir, você concorda em seguir o `CODE_OF_CONDUCT.md` quando ele for
adotado pelo projeto.
