# P227D v1.0 — distinguir Topic Alias não mapeado de valor inválido

Preparado em 2026-10-18 antes de editar testes/runtime. Coordenador autorizou
nova fatia após entrega P227A/matriz no commit135da6c. Fonte0.42.0 integrada
P227A/P227C, sem mudar versão, v15, dependências ou serviço do operador.

## Requisito e RED

OASIS MQTT5 §3.3.4, processamento de Topic Alias, caso3a: alias numérico válido
ainda sem mapeamento e TopicName vazio deve encerrar com DISCONNECT0x82.
Zero ou acima do máximo anunciado continuam Topic Alias invalid0x94.
Fonte oficial conferida pelo agente e coordenador:
https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html

Hoje FrameReader::try_take_packet usa TopicAliasInvalid também no lookup
vazio, e serve_mqtt emite0x94 para os três casos. A fixture P176 fixa0x94 no
terceiro vetor e não é oráculo normativo para esse ramo. Antes do fix, criar
wire independente com caminho ELF explícito/hash/report exclusivo, executar
RED contra cópia congelada0.42.0 SHA46d79faf...809 e preservar resultado.
Adicionar teste unitário tipado para distinção, sem mexer em produção até RED.

## Mudança mínima e ownership

- codec.rs: tipo específico TopicAliasUnmapped somente no lookup sem entrada;
  preservar zero/excesso, estabelecimento/substituição, quotas e escopo local.
- mod.rs: mapear o novo tipo para DISCONNECT0x82 usando write_limited existente;
  fechar antes de PUBACK/PUBREC/mutação de retained/roteamento; Will permanece.
- Fixture verify_mqtt5_alias_error_disconnect.py: expectativas por vetor,
  somente terceiro caso muda0x94→0x82; nunca aceitar ambos como sucesso.
- Script próprio verify_phase6_alias_reason.py e unitários, registro P227D;
  matriz pode atualizar R01 após prova real, sem fechar fase global.

Não editar router/store/CI/Cargo/client/bridge/checklists gerais. Preservar
alterações de outras frentes. Preparar/commitar este prompt localmente antes
dos testes/código; sem push/tag/release própria. Cargo apenas após coordenador
liberar cache (full test original em andamento); nenhum build concorrente.

## Gates e isolamento

Wire: Python padrão, bytes independentes dos encoders Rust; reusar apenas
helpers de fixture privada do P227A, registrar os hashes dos dois scripts.
Estado nativoLinux/portaefêmera/envMQTT limpo, cópia imutável/cleanup limitado,
sem logs/secrets do operador. Invalidos com QoS1/retain não recebem PUBACK nem
entregam/armazenam payload; observador recebe somente Will original e responde
PING; assinante tardio verifica ausência de retained. Zero/excesso e unknown
valid-range exigem reasons distintos; aliases válidos/substituição, conexão
nova e MQTT3.1.1 são controles. Cobrir alias1 e16 ainda não mapeados e máximo
de pacote7 quando cabe aceitação/erro (não presumir aceitação de máximo<7).

Registrar RED e GREEN unitário/wire, SHA/versão/duração/exit/cleanup reais.
Novo build congelado separado não sobrescreve ELF anterior nem sua evidência;
parent coordenará full gates e runner final. Se falhar sem causa comprovada,
preservar FAIL e revisar prompt antes de mudar teste ou implementação.
Sem alegaçãoTLS/mTLS/SLA/certificação/aceite global6A–6D. MIT preservada.
