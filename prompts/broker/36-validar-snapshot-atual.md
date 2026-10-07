# P36 — Gate do snapshot atual, substituto da reprodução 0.2.0

Tipo: validação proposta de recursos existentes; execução não realizada nesta tarefa.
Leia contrato-base, Cargo.toml, CHANGELOG, VERSIONING, matriz MQTT e código.
Não fixar a versão futura: o snapshot inspecionado declara 0.5.0 em desenvolvimento.

## Prompt de trabalho

Confirme versão, commit, plataforma e alterações existentes. Em ambiente autorizado
e isolado, rode gates CONTRIBUTING: fmt, cargo test --locked e Clippy.
Inspecione scripts/license_inventory.py --check e scripts/verify_interop.py antes
de executar; este último precisa Python 3.11+, Mosquitto clients e stdbuf no Linux.
O CI Ubuntu contém esses gates, mas seu arquivo não prova uma execução recente.
Não instalar ferramentas automaticamente; ausência resulta em BLOCKED.

Valide QoS 0/1/2, ACKs, retained substituído/removido, sessões persistentes,
fila offline, takeover, UNSUBSCRIBE, filtros +/#, níveis vazios, $, sobreposição,
ACL literal, revalidação na entrega/restore e limites. Last Will deve continuar
rejeitado enquanto não implementado. MQTT 5 fora do escopo.
O script existente cobre open-lab; prepare gate separado com credenciais novas
para password-lab, acl-lab e secure-mtls, negativos de CA/SAN/senha/ACL, sem
alterar o serviço real. Certificados precisam de ambiente e autorização adequados.
Inclua clientes independentes além do próprio codec; não confundir fixture wire
independente com biblioteca cliente completa. Crash de processo não prova perda de energia.

## Aceite

Matriz capability -> requisito -> teste -> resultado real -> ambiente. PASS,
FAIL, BLOCKED, NOT_IMPLEMENTED e NOT_APPLICABLE separados. Registre lacunas
de carga, fuzzing, TLS/ACL externa e operação; não declarar MQTT completo ou produção.
