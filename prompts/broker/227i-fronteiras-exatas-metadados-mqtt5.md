# P227I v1.1 — fronteiras exatas de metadados MQTT5

Preparado em2026-10-18 antes dos testes, por solicitação do coordenador da
fase6. Entrada: broker0.42.0, HEAD1f25c4c, P227E88906d6 integrado; mod.rs e
router.rs em correção paralela E, preservados. A matriz P227A ressalva2
declara limites implementados, mas sem todos os vetores exatos Will/UP16.
Owner E transferiu codec.rs para esta contribuição antes de sua edição;
Cargo/cache permanecem exclusivos de E até o freeze informado à raiz.

## Escopo e invariantes

Somente testes no módulo cfg(test) de src/mqtt/codec.rs, este prompt e
registro próprio. Nenhuma mudança de parser/encoder runtime, router, clock,
store, handler, dependência, quota, versão, CI ou formato persistido. Não
declarar aceite global, cobertura combinatória completa ou certificação.
Se os vetores revelarem defeito, preservar FAIL e avisar o coordenador;
uma correção runtime exige revisão do prompt e ownership específico antes.

Usar as skills locais xmqr-rust-mqtt, xmqr-tests e xmqr-security-review:
inputs sintéticos limitados, oráculos independentes em bytes, positivos e
negativos de limite; não ler dados/segredos reais nem tocar serviço/host.

## Vetores e resultados observáveis

Tetos256/16/2048 são decisões locais, não os máximos universais do MQTT.
256/257 contam bytes UTF8, não caracteres. UP16 conta cada propriedade
com ID1byte e os dois prefixosU16:5+len(chave)+len(valor);2048/2049 referem
ao bloco de User Properties, não ao Property Length VBI nem ao pacote todo.

| Propriedade/fronteira | Entrada | Saída |
| --- | --- | --- |
| Content Type256/257 UTF8 |Will e PUBLISH|encoder PUBLISH|
| Correlation Data256/257 binária, inclusive00/ff |Will e PUBLISH|encoder PUBLISH|
| User Property chave256/257, valor256/257 |Will/PUBLISH/SUBSCRIBE/UNSUBSCRIBE|encoder PUBLISH|
| User Property16/17 pares abaixo do teto de bytes |mesmos4contextos|encoder PUBLISH|
| User Property2048/2049 bytes, campos<=256 e4pares |mesmos4contextos|encoder PUBLISH|

256válido preserva bytes;257recusado sem truncar/normalizar. Os16pares
válidos incluem duplicatas exatas e chaves repetidas com valores diferentes,
na ordem fornecida. Bloco2048 válido usa três pares com campos256/256 e um
par256/236:3x517+497=2048; a diferença2049 é só o último valor237. Assim a
recusa isola o teto total, não o teto de campo ou quantidade de pares.

Criar campos/propriedades/corpos e VBI canônico com utilitários cfg(test)
independentes, sem chamar Cursor/encode_length/parse_subscription_user_property
ou os validadores para montar expectativas. Decoder recebe corpo construído
fora do encoder. Encoder PUBLISH deve igualar frame completo independente,
não somente roundtrip no decoder próprio. Will/PUBLISH decodificados devem
igualar metadados completos; SUB/UNSUB aceitam e descartam User Properties
por política atual, logo seus testes verificam filtros/IDs preservados,
não alegam retenção de metadados inexistente nesses tipos.

Não exigir códigos0x81/82/95 para excesso local genérico: refusa estrita
deve impedir Packet válido/sucesso da função, preservando a classificação
atual. Ordem, duplicatas e dados binários serão comparados nos contextos que
os retêm. Content Type/Correlation Data não são propriedades SUB/UNSUB;
não inventar suporte nesses contextos para executar a tabela.

## Referência e validação

Fonte oficial OASIS MQTT5 OS07/03/2019, consultada nesta contribuição:
https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html
Will §§3.1.3.2.5/.7/.8, MQTT-3.1.3-10; PUBLISH §§3.3.2.3.6/.7/.9,
MQTT-3.3.2-16/-17/-18/-19; SUB/UNSUB §§3.8.2.1/3.10.2.1. Apenas vínculos
e paráfrases; não copiar especificação/licenças de terceiros para o runtime.

Executar somente rustfmt localizado no codec e git diff --check nesta
frente; nenhuma chamada Cargo em paralelo. Coordenador executará filtro
p227i_, suíte codec/regressão, fmt/test/clippy locked depois do freeze.
Registro distinguirá NOT_RUN/PASS/FAIL reais, fonte/hash, comandos, ambiente
e limites. Criar testes não equivale a aprovação, integração wire, TLS/mTLS,
persistência, interoperabilidade externa ou homologação de plataforma.
Sem push/tag/publicação ou alteração dos arquivos de outros owners.

## Revisão v1.1 — corrigir somente o contexto do decoder de teste

Coordenador executou p227i_ na fonte preparada:9testes,3PASS/6FAIL,
compile2.07s/testes0.02s. Seis falhas ocorreram no unwrap do controle Will,
Err SecondConnect: helper decoded usou decode_for(...,true), que representa
uma conexão MQTT5 já estabelecida e deve recusar um segundo CONNECT. Isso
é erro do launcher do teste, não falha do parser contra esses metadados.
Preservar esse resultado e as expectativas originais, sem alterar máximos,
bytes, classificação de excesso ou regras de CONNECT para tornar verde.

Corrigir apenas helper cfg(test): Context::Will chama decode inicial, que
descobre MQTT5 no próprio CONNECT; demais contextos usam decode_for com
MQTT5true. Repetir nove grupos, suíte codec e Clippy no cache confirmado
liberado por E, locked/offline/-j1 e TMPDIR=/var/tmp, sem concorrência. A
raiz transferiu esta execução após encerrar o uso de Cargo por E. Rustfmt
continua localizado. Se outro defeito aparecer, registrar antes de mudar.
