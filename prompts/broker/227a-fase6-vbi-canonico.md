# P227A v1.0 — Variable Byte Integer canônico no MQTT 5

Preparado em 2026-10-18 antes de testes/correção. Coordenador reservou
`src/mqtt/codec.rs` para esta frente; `mod.rs` somente após novo aviso explícito.
Entrada: broker0.42.0, HEAD505c3ce78c00dde2bcd4949a391c361c41647f81,
P227 master aceito, estado v15. Preservar alterações de outras frentes/client.

## Requisito e escopo

OASIS MQTT5 §1.5.5, MQTT-1.5.5-1 exige codificação com o mínimo de bytes.
Confirmado na fonte oficial:
https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html
O parser atual limita a quatro bytes, mas não valida minimalidade de Remaining
Length ou VBI internos (Property Length e Subscription Identifier).

Criar RED unitário/wire independente antes da correção, depois rejeitar VBI
não mínimo em MQTT5 em todos os contextos comuns. Após CONNACK, Malformed
Packet deve tentar DISCONNECT0x81 limitado pelo tamanho negociado e fechar
antes de qualquer mutação do quadro. CONNECT5 inicial não pode autenticar,
criar sessão/Will ou receber CONNACK de sucesso com codificação inválida;
CONNACK0x81 somente quando versão/limite puderem ser inferidos com segurança.
Corpo incompleto/EOF/I/O não serão reclassificados como VBI não mínimo.

Escopo: codec.rs, testes in-module, `scripts/verify_phase6_vbi.py`, este prompt
e registro P227A. Não alterar router/store/CI/Cargo/docs gerais/client/bridge.
Reusar os tipos de erro/mapeamentos existentes quando suficiente. Subprompt
será commitado localmente antes do código; sem push, tag ou publicação de
reprodução detalhada antes de corrigir. Builds pesados ficam com coordenador.

## Compatibilidade e invariantes

MQTT3.1.1 preserva o framing histórico, inclusive Remaining Length não mínimo
admitido pelo teste de quota P58; nenhum endurecimento implícito desse protocolo.
MQTT5 mantém todos os valores canônicos legais, limites de pacote/buffer,
fragmentação/concatenação, propriedade repetível/única, ACL, QoS, retained,
sessões, Will e durabilidade. Rejeitar antes de encaminhar ao roteador.
Não alterar documento v15, versões, dependências ou configuração do operador.

## Aceite e evidência

- Tabela de valores canônicos nas fronteiras0/127/128/16383/16384/2097151/
  2097152/268435455, codificações redundantes de2/3/4bytes e cabeçalhos parciais.
- Remaining Length MQTT5 (conexão estabelecida e CONNECT inicial), Property
  Length em CONNECT/Will/PUBLISH/SUBSCRIBE/UNSUBSCRIBE/ACK/AUTH/DISCONNECT e
  Subscription Identifier; MQTT3.1.1 e quadros canônicos como controles.
- Wire independente com broker privado/cópia imutável, porta efêmera,
  filesystem nativo Linux em /var/tmp, env MQTT limpo, prazos/cleanup limitados;
  fechamento/reason code, nenhuma publicação/assinatura/ACK parcial e Will
  aplicável. Sem credenciais reais, logs/payloads do operador ou C:/x81.
- Avisar coordenador antes de cargo; targeted -j1 para RED/GREEN e fmt/check
  proporcionais. Principal coordenará suíte/Clippy/release finais no snapshot
  integrado. Registrar hashes/comandos/FAIL/PASS/BLOCKED reais sem aceitar6A
  global por esta fatia. Revisar prompt antes de corrigir falhas inesperadas.

Não confundir correção normativa com garantia de produção, SLA ou nova
homologação de plataforma. Ferramenta ausente é BLOCKED, nunca instalar só
para satisfazer o gate. MIT/notices e ownership dos arquivos preservados.
