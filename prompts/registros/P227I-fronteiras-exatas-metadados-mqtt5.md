# P227I — fronteiras exatas de metadados, testes preparados

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
