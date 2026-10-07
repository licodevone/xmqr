---
name: xmqr-tests
description: "Planejar e executar testes do XMQR quando solicitado ou para validar uma mudança funcional, distinguindo evidência interna, externa e gates bloqueados."
---

# Testes e evidências do XMQR

Leia [AGENTS](../../../AGENTS.md), [CONTRIBUTING](../../../CONTRIBUTING.md),
[matriz MQTT](../../../docs/conformance/mqtt311-status.md) e
[gate atual P36](../../../prompts/broker/36-validar-snapshot-atual.md).
Para criar/modificar testes, prepare primeiro o prompt; execução autorizada de
testes existentes não exige alteração documental prévia nem nova permissão duplicada.

Gates reais: cargo fmt --all -- --check; cargo test --locked;
cargo clippy --locked --all-targets -- -D warnings.
Escolha negativos e integração para o risco alterado: frames independentes do
encoder, fragmentação/concatenação, flags/identifiers, QoS/replay, ACL,
quota, retained, takeover e crash em limites de commit em cópias isoladas.
Não escrever testes que apenas reproduzam o texto ou implementação.

CI Ubuntu contém python3 scripts/license_inventory.py --check e build --bins.
Interop: python3 scripts/verify_interop.py --broker target/debug/mqtt-broker
quando esse for o CARGO_TARGET_DIR confirmado. O script requer Python 3.11+,
Mosquitto clients e stdbuf; confirme antes de executar. Não instalar automaticamente.
Ele cria recursos temporários/serviços de teste: execute só quando o pedido
autorizar esse gate, nunca sobre a instância ou estado do usuário.

A evidência externa documentada cobre open-lab. Não marcar TLS/mTLS/ACL externa
como comprovada por ela. Gate TLS precisa de ambiente isolado, CA/SAN válidos,
identidades distintas e negativos; não publicar secrets. Cliente próprio não é
oráculo suficiente. Crash de processo não prova energia; ausência de ferramenta
é BLOCKED. Distinguir PASS/FAIL/BLOCKED/NOT_IMPLEMENTED/NOT_APPLICABLE.

Para docs/configuração, validar formato/links/escopo basta; esta skill não obriga
rodar Rust ou serviços. Entregue comandos, códigos de saída, cenários, ambiente
e limites reais em [registro](../../../prompts/registros/TEMPLATE.md).
