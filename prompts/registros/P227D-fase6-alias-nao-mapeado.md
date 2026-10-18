# P227D — Topic Alias não mapeado, em validação wire

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

## Wire candidato e limites

Novo build/cópia congelada separados do ELF anterior ainda pendentes.
Script8casos exige bytes/reasons exatos; inválidos QoS1/retain não recebem
PUBACK nem mutam retained/entrega, Will original preservado, barreiraPING e
assinante tardio. Fixture privada do P227A reaproveitada somente para processo,
conexões e codificação de bytes Python, nunca encoder Rust como oráculo.
JSON exclusivo com hashes de ambos scripts/ELF, versão, tempos e cleanup.

Escopo open-labTCP sintético, não provaTLS/mTLS/certificação/SLA/fase6global.
Sem commit de caminhos alheios, push/tag/release/instalação/serviço do operador.
Skills xmqr-tests/xmqr-security-review/xmqr-rust-mqtt orientaram RED antes do fix,
diagnóstico tipado, controle3.1.1, isolamento e evidência limitada. MIT preservada.
