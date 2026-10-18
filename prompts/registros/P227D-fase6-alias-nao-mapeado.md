# P227D — Topic Alias não mapeado, GREEN direcionado

Data2026-10-18. Prompt inicial commitado localmente8a8bf07 antes de testes e
runtime; revisão v1.1 antes da correção. OASIS MQTT5 §3.3.4, caso3a, confirmado
na fonte oficial: valor de alias válido sem mapeamento e TopicName vazio usa
DISCONNECT0x82, distinto de alias zero/excessivo0x94.

## RED preservado

ELF integrado anterior `mqtt-broker0.42.0`, SHA256
`46d79faf91220cdd59e43602c8f3528a2654463a6f71408c542a9c8638b4f809`:
`verify_phase6_alias_reason.py --label baseline --state-root /var/tmp`,8casos,
4PASS/4FAIL, exit1, cleanupPASS,2.232s. Somente alias1/16 não mapeados,
nova conexão e MPS7 retornaram0x94 onde esperado0x82; controles de zero,
excesso, estabelecer/usar/substituir e MQTT3.1.1 passaram. Report preservado
`../.artifacts/p227d-alias-baseline-1.json`, harnessSHA256
`e88a707af7beaebdc0318b9adade3d716adb0047ec15dc4a9e96a6e838fc7937`,
helper P227A SHA256
`ccc8ecae90ccd18ecc98d27dc8876ad42453a2f2663576f853b6ff38f07fb064`.

Unitário independente do encoder no fonte pré-fix:
`TMPDIR=/var/tmp cargo test --locked -j1 --lib mqtt5_unmapped_alias_ -- --nocapture`:
1FAIL planejado, compile25.02s, teste0.04s, launcherWSLexit1. Tipo anterior
TopicAliasInvalid reproduzido; nenhuma falha ambiental/startup/compilação.

## Correção e GREEN direcionado

Somente `codec.rs`: novo erro `TopicAliasUnmapped` no lookup ausente;
`mod.rs`: novo ramo limitado0x82. Zero/excesso ainda usam TopicAliasInvalid e
0x94. Nenhuma tabela/quota/ACL/roteamento/v15/credencial/protocolo3.1.1 mudou.
Fixture P176 agora exige reason por vetor, sem aceitar ambos como sucesso.
Unitário novo tipado e teste de reset existente atualizados.

`TMPDIR=/var/tmp cargo test --locked -j1 --lib alias -- --nocapture`:
3/3PASS, exit0, compile31.86s, teste0.02s. Rustfmt dos dois módulos PASS,
AST dos2scripts PASS, git diff --check PASS. Coordenador liberou cache antes
de cada cargo; nenhum full test/Clippy/release foi iniciado por esta frente.

## Diagnóstico de fixture, preservando o FAIL

Builddebugbroker exclusivo-j1 terminou38.88s, exit0; cópia congelada separada
`../.artifacts/p227-binaries/mqtt-broker-p227d-0.42.0`, runtimecommitd28f832,
versão real `mqtt-broker0.42.0`, SHA256
`dca22b2624b7f36175d4e939c640b6f5730220bcc9510580eef9054a6af8ef57`.
ELF integrado anterior permaneceu intacto. Nenhum Cargo da frente ativo depois.

Candidato1:7PASS/1FAIL,2.351s, exit1, cleanupPASS, report exclusivo
`../.artifacts/p227d-alias-candidate-1.json`, harnessSHA256
`e02b3dfae07e9b5e503a2733e29acad3d972790e48a6e9d2f339aef43da8b9df`.
Falha somente no vetor MPS7. Diagnóstico privado no mesmoELF confirmou
CONNACK `(0x20,0000022a01)` sem TopicAliasMaximum; portanto máximo anunciado0,
alias1 excede esse valor e0x94 está correto. A fixture presumia anúncio16.
Esse vetor era falso pressuposto também no baseline1; os demais três vetores
de unknown-alias do baseline1 continuam RED real. Não foi alterado runtime.

Promptv1.2 antes do marcador final de sucesso para o runner; v1.3 antes de
corrigir fixture: manter MPS7→0x94 e acrescentar MPS15 com anúncio16→0x82,
total9casos. Agora verifica CONNACK bruto/exato antes dos reason codes. Não
aceita reasons alternativos nem remove testes/asserts. Reports anteriores
preservados. Baseline2 no ELF antigo46d79faf:5PASS/4FAIL,2.561s, exit1,
cleanupPASS; `../.artifacts/p227d-alias-baseline-2.json`.

## Wire GREEN e limites

Mesmo harness corrigido9casos no ELF novo dca22b26:9/9PASS, exit0,
cleanupPASS,2.756s, `../.artifacts/p227d-alias-candidate-2.json`.
HarnessSHA256:`a9ee09a42bf481a65c1a36177a85a4ac434a0097b25ddad21999647be3de73ed`;
helperSHA permanececcc8ecae completo acima. Marcador final
`P227_ALIAS_REASON_PASS` emitido somente após PASS global/cleanup.
Comandos usam Python3 padrão no WSL e `--broker` explícito a cada cópia:

```sh
python3 scripts/verify_phase6_alias_reason.py \
  --broker ../.artifacts/p227-binaries/mqtt-broker-p227d-0.42.0 \
  --label candidate --state-root /var/tmp \
  --report ../.artifacts/p227d-alias-candidate-2.json
```

Inválidos QoS1/retain não recebem
PUBACK nem mutam retained/entrega, Will original preservado, barreiraPING e
assinante tardio. Fixture privada do P227A reaproveitada somente para processo,
conexões e codificação de bytes Python, nunca encoder Rust como oráculo.
JSON exclusivo com hashes de ambos scripts/ELF, versão, tempos e cleanup.
P227A VBI também repetido no novoELF:21/21PASS,3.963s, cleanupPASS,
`../.artifacts/p227a-vbi-p227d-candidate-1.json`. Matriz documental atualizada
para contexto/diag/tipo/teste, estado IMPLEMENTED_TEST_AVAILABLE preservado.

Escopo open-labTCP sintético, não provaTLS/mTLS/certificação/SLA/fase6global.
Sem commit de caminhos alheios, push/tag/release/instalação/serviço do operador.
Skills xmqr-tests/xmqr-security-review/xmqr-rust-mqtt orientaram RED antes do fix,
diagnóstico tipado, controle3.1.1, isolamento e evidência limitada. MIT preservada.
