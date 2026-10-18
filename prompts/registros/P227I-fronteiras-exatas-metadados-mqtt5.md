# P227I — fronteiras exatas de metadados, testes direcionados aprovados

2026-10-18, Windows/PowerShell, Rustfmt1.9.0-stable. Entrada do prompt:
broker0.42.0/HEAD1f25c4c, P227E88906d6 integrado; mod/router em trabalho E.
Coordenador confirmou transferência de codec.rs antes desta edição. Prompt
v1.0 prompts/broker/227i-fronteiras-exatas-metadados-mqtt5.md foi criado e
lido antes do código, com vetores/tetos/oráculos/ownership/validação.

## Escopo efetivamente alterado

Somente módulo cfg(test) p227i_metadata_boundaries, acrescentado ao final
de src/mqtt/codec.rs, este registro e o prompt. Diff do codec é367 linhas
adicionadas, nenhuma linha runtime alterada. Nenhum Cargo/lock, formato16,
quota, handler/router/store/clock, dependência ou arquivo de outro owner foi
editado. Rustfmt usou skip_children=true para não formatar módulos vizinhos.

Nove grupos #[test], ainda NOT_RUN:

| Grupo | Oráculo |
| --- | --- |
| Will Content Type |256bytes ASCII/UTF8 aceitos e257 recusados|
| PUBLISH Content Type |mesmos limites no decoder e encoder/frame exato|
| Will Correlation Data |256bytes00..ff preservados e257 recusados|
| PUBLISH Correlation Data |mesmos limites no decoder e encoder/frame exato|
| Campos User Property |chave e valor256/257 isolados, ASCII/UTF8,4contextos e encoder|
| Quantidade User Property |16pares duplicados em ordem aceitos;17 recusados,240/255bytes|
| Total User Property |2048aceito/2049recusado,4pares e campos<=256,4contextos e encoder|
| Metadados combinados |duplicatas UP intercaladas com CT/CD, preservação de bytes e ordem|
| Contexto SUB/UNSUB |não aceitar CT/CD como se fossem User Property|

Os quatro contextos são Will/PUBLISH/SUBSCRIBE/UNSUBSCRIBE. SUB/UNSUB validam
e descartam essas propriedades diagnósticas; testes conferem packetID/filtro/
QoS/opções preservados, sem afirmar retenção inexistente. Apenas Will e
PUBLISH comparam todo o vetor UP, bytes CD e string CT. Nenhuma combinação
excluída pela tabela recebe promessa implícita de cobertura.

Construtores sintéticos independentes montam prefixosU16 e VBI canônico
limitado aos pequenos vetores. Não chamam Cursor/encode_length/validador
do codec. Decoder recebe corpo independente do encoder; saída do encoder é
comparada ao frame completo esperado, não só ao roundtrip próprio. O teto
UP inclui5bytes por par:3x517+497=2048, último valor236→237 cria2049 sem
violar256porcampo nem16pares. Emissões podem reordenar CT/CD, mas UP mantém
a mesma ordem/duplicatas. Os tetos são locais, não máximos normativos MQTT.

## Validação realmente executada

```text
rustfmt --edition 2024 --config skip_children=true src/mqtt/codec.rs
git diff --check -- src/mqtt/codec.rs prompts/broker/227i-fronteiras-exatas-metadados-mqtt5.md
```

Ambos exit0/PASS. Rustfmt faz parsing de sintaxe, não substitui compilação
ou execução. SHA256 do codec preparado:
d559aaac8fa39c572cb5a085058595147983c1e02a437cd122e7cd269a905546.
Nenhuma execução Cargo por esta frente: cache pertencia a E; coordenador
receberá freeze e executará o filtro p227i_ e gates proporcionais depois.

| Gate | Estado neste checkpoint |
| --- | --- |
| Rustfmt localizado/diff whitespace |PASS|
| Compilação e nove grupos p227i_ |NOT_RUN|
| Suíte codec/completa/Clippy/build |NOT_RUN por esta frente|
| Wire/TLS/mTLS/interoperabilidade/durabilidade |Não cobertos por estes testes de codec|

Se aparecer FAIL, preservar resultado/oráculo e avisar antes de corrigir
runtime. Não se anuncia segurança, certificação, cobertura combinatória ou
aceite global6A–6D. MIT preservada. Skills Rust/testes/segurança orientaram
fronteiras, negativos e independência do oráculo, sem substituir os gates.
Referências OASIS foram conferidas pelo link oficial do prompt, sem copiar
texto normativo para o produto. Sem serviço, segredo, dado real, push/tag
ou publicação. Commit/gates finais ficam coordenados com o mantenedor.

## Revisão v1.1 — falha real do helper e correção mínima

O checkpoint de preparação acima continua histórico, não foi convertido em
PASS retroativo. A raiz integrou os nove grupos em cf6cef4 e executou o
filtro:9testes,3PASS/6FAIL,compile2.07s/testes0.02s. Os seis grupos com Will
falharam no controle positivo, codec4406 unwrap Err SecondConnect. O helper
chamava decode_for(header,body,true): esse boolean representa conexão MQTT5
já estabelecida, na qual CONNECT é corretamente recusado. Portanto foi um
erro de contexto da fixture, não evidência de bug do parser nos metadados.

Promptv1.1 em c1b9c97 precedeu a correção do helper. Apenas Context::Will
agora chama decode inicial, que identifica a versão no CONNECT; demais
contextos mantêm decode_for(...,true). Diff funcional do codec:3linhas
adicionadas/1removida. Máximos, bytes sintéticos, construções, tipos de
refusa, controles válidos e expectativas de ordem/duplicatas inalterados.
Não houve modificação no runtime para tornar verdes os testes.

## Gates reais posteriores

Raiz liberou Cargo/cache após E encerrar sua execução. WSL Ubuntu26.04,
Ruststable1.99, target padrão do repositório, sem override CARGO_TARGET_DIR,
TMPDIR=/var/tmp. Cargo usado pelo caminho explícito da toolchain estável,
com seu bin no PATH do processo; sem instalação/network/limpeza de cache.

```text
cargo test --locked --offline -j1 --lib p227i_ -- --nocapture
cargo test --locked --offline -j1 --lib mqtt::codec::
cargo clippy --locked --offline -j1 --all-targets -- -D warnings
```

| Gate | Resultado real | Compilação/check | Testes |
| --- | --- | --- | --- |
| Filtro p227i_ |9PASS,0FAIL,exit0|11.56s|0.01s|
| Codec completo, incluindo P227I |78PASS,0FAIL,6ignored,exit0|2.29s|0.05s|
| Clippy all-targets/-Dwarnings |PASS sem avisos,exit0|15.15s|—|
| Rustfmt localizado e diff --check |PASS,exit0|—|—|

Os seis ignored são campanhas P90 explícitas, não propriedades P227I
ignoradas nem campanha de fuzzing executada por este comando. Os filtros
se sobrepõem: não somar9+78 como87 casos distintos. Não foi rodada suíte
global, build de bins/release ou nova campanha wire por esta frente.
Runtime E de entrada já era c3713c839e17020d76dbca60e737c36c9b271860;
essa contribuição apenas ajustou o contexto de teste após registrar o RED.

SHA256 final do codec neste freeze:
279eb28a179c5abfbc9f930e601b748af3a99796f3b0a8b0c2e172f7674295a7.
Cache liberado para a raiz após Clippy. A ressalva2 da matriz P227A agora
tem evidência direcionada para os exatos vetores descritos, não para todo
produto cartesiano de propriedades, QoS, estado, transporte ou plataforma.
Atualização do aceite/checklist global, artefatos e distribuição permanece
com o coordenador. Sem push/tag/publicação nesta contribuição.
