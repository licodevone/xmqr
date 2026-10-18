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

## Revisão v1.1 — RED confirmado antes da correção

Oito unitários novos no fonte0.42.0:2controlesPASS/6FAIL (launcher WSL exit1), reproduzindo
aceitação de RL não mínimo, Property Length e Subscription Identifier.
Wire em cópia privada do ELF0.41.0 explicitamente baseline:20casos,
2PASS/18FAIL, cleanupPASS, report exclusivo p227a-vbi-baseline-1.json.
Falhas planejadas RED não serão apagadas nem confundidas com teste do candidato.
Agora corrigir apenas codec: VBI internos sempre canônicos (são campos5),
framing estrito após negociação5 e CONNECT5 inicial identificável, preservando
frame_header/RemainingLength3.1.1. Cabeçalho inválido já completo pode recusar
antes de aguardar corpo; prefixo parcial permanece aguardando conclusão.

## Revisão v1.2 — reforço dos controles wire antes do candidato

Targeted GREEN no fonte corrigido:8/8PASS, sem mod.rs. Antes do ensaio final,
reforçar o controle3.1.1 para CONNECT inicial com RL histórico não mínimo,
além do PINGREQ. Após CONNECT5 inválido, observador independente não pode
receber o Will do pedido recusado (barreira PING e janela negativa limitada).
Não diminuir nenhuma asserção RED, trocar reason code ou contar baseline0.41
como candidato0.42. O harness final registra seu próprio SHA, versão e ELF
privado exato; build final coordenado pelo agente principal.

## Revisão v1.3 — falha de startup também deixa JSON e cleanup

Antes do candidato, separar criação/início do processo privado no harness para
que falha de readiness/Popen também atravesse cleanup e gere report FAIL, sem
falso PASS por lista vazia. Nenhum processo do operador ou timeout de protocolo
muda. BaselineRED original permanece com hash e contagem originais.

## Revisão v1.4 — matriz de propriedades antes da consolidação 6A

Coordenador autorizou também ownership exclusivo de
`docs/conformance/mqtt5-property-matrix.md`. Antes de criá-la, levantar no
codec/handlers e nos testes reais: contexto/direção, ID/tipo, multiplicidade,
valores e tetos locais, requisito OASIS, símbolo e testes específicos.
Cobrir CONNECT/Will/PUBLISH/SUBSCRIBE/UNSUBSCRIBE/ACK/AUTH/DISCONNECT e
emissão CONNACK, incluindo VBI, UTF-8, propriedade desconhecida e fronteiras.

Usar IMPLEMENTED_TEST_AVAILABLE como estado de evidência até gates integrados;
não confundir teste disponível com executado no ELF final. Separar entrada
aceita de emissão opcional ausente (Response Information/Reason String não
viram obrigação artificial). Registrar limites locais e rejeições reais sem
afirmar certificação ou cobertura exaustiva de todos os motivos de erro.
Não editar mqtt5-status/plano/evolution/README ou código adicional nesta etapa.
Adaptar a organização da skill doc-coauthoring ao contexto já fornecido pelo
coordenador, sem perguntas redundantes; revisão independente de leitura fica
pendente se não houver slot livre. Commit local somente dos caminhos próprios
foi autorizado, sem push/tag/versão. Fonte do codec permanece congelada.
