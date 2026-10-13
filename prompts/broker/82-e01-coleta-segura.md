# P82 v1.3 — coleta E01 restrita, limitada e sem falso positivo

Estado de entrada: HEADcaa68eed80b84c5880b8c96d9ed15e2b381c0579,
broker/admin0.11.4 e cliente independente0.8.1. E01 tem backup/flash/boot reais,
mas MQTT físico NOT_RUN por alvo Wi-Fi2,4GHz não encontrado. Trabalho Windows
limpo; preservar tarballs preexistentes não rastreados no client.

Pedido: continuar atualizações com prompts/testes/MIT/commit/push e publicação
de marcos validados. Esta fatia continua fase2, não antecipa fase3.

## Objetivo e achados

O runner P81 aceita qualquer linha E01 com caracteres genéricos e decide PASS
pela presença de strings, sem ordem ou veto a FAIL. Uma linha inesperada poderia
vazar texto, e um transcript contraditório/incompleto poderia receber PASS.
Não foi observado vazamento real nem aprovação física indevida no P81.

Implementar parser fechado de markers, validação da sequência por execução,
veto a falha/reboot/duplicatas de milestones, teto de bytes/markers e deadline.
Separar testes sintéticos do coletor de evidência física MQTT.
Adicionar modo monitor-only para observar firmware já instalado sem flash,
Docker, novas credenciais ou instalação. Registrar firmware-source desconhecido
nesse modo: não atribuir código atual ao firmware antigo.

Arquivos: validation/esp32-e01/{evidence.py,test_evidence.py,run_initial.py,
test_run_initial.py,README.md}, docs/esp32-phase2-checklist.md,
docs/phase2-acceptance.md, prompts/registros/P82-e01-coleta.md e relatório sanitizado.
Não alterar kernel, Cargo manifests/lock, firmware, admin, runtime CLI, versões,
quota/estado/protocolo ou credenciais. Sem expansão de dependências.

## Requisitos

- Lista fechada: boot0.1.0/payload1024; associação/IP/SNTP/mTLS;
  QoS0→1→2 bytes1024; PASS→STOP. AP/canal/RSSI/auth e motivos numéricos
  só pelos formatos previstos. FAIL só com nomes de etapas do firmware.
- Não imprimir ou guardar linhas desconhecidas, SSID/senha/keys/payloadreal.
  Não aceitar prefixo, UTF-8 inválido, bytes truncados ou linha sem newline.
  Excesso/erro/ordem inválida/timeout impede PASS. STOP sozinho não é sucesso.
- No máximo128markers,64KiB totais e512bytes por linha; deadline180s padrão,
  argumentos1..180s. Até prazo máximo, buffering limitado sem busy-loop.
- Monitor-only opcional inicia serial/reset normal na COM especificada e
  observa marcadores existentes; nunca escreve flash/NVS ou cria containers.
  Resultado não equivale a fase2 completa e não prova fonte/identidade do firmware.
- Arquivo de relatório novo/único privado por execução; preservar resultadosP81.
  Erros apenas códigos fixos; não repassar exceção com texto vindo da placa.
- Nenhuma mudança de rede/firewall/roteador, fallback insecure ou rede alternativa.

## Validação e aceite

Testes determinísticos para sequência válida, falta/ordem/FAIL/reboot/múltiplos
boots/duplicatas, linhas com segredos sintéticos, negativos numéricos, framing
fragmentado/CRLF/linha longa/sem newline, limites e timeout por relógio fake.
Testar monitor-only sem Docker/flash, persistência sem sobrescrever, hardware
diagnóstico somente seCOM4 acessível; não regravar placa com Wi-Fi indisponível.
Fmt do firmware/inventário preservados; Python unittest/sintaxe/diff/links e
auditoria de secrets pertinentes. Não chamar testes sintéticos de MQTT real.

Evidência PASS/FAIL/BLOCKED/NOT_RUN; commit/push autorizados. Runtime0.11.4/0.8.1
sem mudança, portanto sem nova tag/release/.deb/Hub ou alteração de tags existentes.
Preservar licença MIT própria e licenças declaradas. Expor Wi-Fi indisponível e
gates físicos restantes; não encerrar fase2 nem avançar fases.

## Revisão v1.1 — falha reproduzida após STOP

35testes iniciais passaram. Negativo adicional fragmentado em1byte mostrou
PASS incorreto se FAIL viesse no chunk seguinte ao STOP. Antes de corrigir:
test_fail_after_stop_in_next_chunk_vetoes_pass retornou1/FAIL.
Após STOP, drenar no máximo1segundo (sempre dentro do deadline/tetos), vetando
markers/linhas incompletas posteriores. A janela é limitada e não garante
autenticidade do firmware nem captura eventos indefinidamente depois do fim.

## Revisão v1.2 — finalização mesmo com erro de relatório/limpeza

36testes passaram; monitor-only real observou boot/erro Wi-Fi alvo ausente/STOP,
sem flash/Docker. Revisão mostrou que erro ao salvar relatório impedia cleanup
e erro em stop impedia tentativas rm/volume. Separar finalização: tentar cada
limpeza exclusivamente dos recursos criados pelo runner, registrar somente
códigos fixos, salvar relatório depois e vetar PASS se cleanup falhar.
Adicionar negativos com mocks; não iniciar containers para testar esses erros.

## Revisão v1.3 — teto exato de entrada

40testes passaram. Asserção adicional do teto total reproduziu leitura de
65664bytes antes da recusa (um chunk excedente). Restringir tamanho de cada
read ao orçamento restante e recusar ao esgotar64KiB, sem nova leitura.
Manter prazos, framing e janela pós-STOP; repetir todos os testes.
