# P84 v1.2 — retained físico com observador wire independente

Base512e051812e0b672bd83fe18552ee8ff275c1a88; main limpa, broker/admin0.11.4,
client0.8.1 independente/intocado. P83 confirmou Wi-Fi/IP/SNTP/mTLS e bytes1024
QoS0/1/2 na COM4. Client tem dois tarballs preexistentes que serão preservados.
Pedido: continuar aproximação funcional a Mosquitto; próxima dependência E01,
sem pular fase2 ou iniciar MQTT5/listeners/bridge em paralelo.

## Objetivo/escopo

Validar retenção criada/atualizada/excluída pelo ESP32 e replay a assinante novo,
com observador Python wire sem encoder Rust/SDK e identidade mTLS distinta.
Observer não é libmosquitto: interop Mosquitto2.0.22 C43 permanece evidência
separada. Confirmar também bytes dos três loopbacks no wire recebido pelo host.

Arquivos validation/esp32-e01/{build.rs,src/main.rs,src/retained.rs,evidence.py,
run_initial.py,retained_observer.py,prepare_retained.py,test_retained_observer.py,
test_prepare_retained.py,test_evidence.py,README.md}; docs/{esp32-phase2-checklist.md,
phase2-acceptance.md,evolution-plan.md,plano-paridade-mosquitto.md,
results/p84-e01-retained-2026-10-13.json}; prompts/registros/P84-e01-retained.md.

Firmware opt-in por XMQR_E01_RETAINED=1 e runner --retained; default P83 e
monitor-only permanecem compatíveis. Não mudar Cargo.lock/core/CLI/versões/MIT,
quota broker, documento durável ou profiles. Código próprio MIT, SDK separado.

## Estado e protocolo

- Preservar backup original em duas leituras4MiB antes de flash COM4; confirmar
  porta/chip existentes, build privado e app≤1MiB. Sem erase geral/NVS/efuses/GPIO.
- Reusar somente CA/servidor/board do laboratório privado vigente; preparar
  diretório novo/exclusivo com certificado/usuário/senha de observer distintos,
  vínculo SHA256 e ACL mínima. Originais/relatórios anteriores não sobrescritos.
- Board: publish bytes/retained, subscribe bytes/control. Observer: subscribe
  bytes/retained, publish somente control. Sem wildcard/permissão implícita.
- Observer TLS CA/SAN/validade, CONNECT3.1.1 CleanSession, IDs próprios. Entrada
  packet≤4096, até32frames/operação, deadlines finitos; sem payloads/segredos em
  stdout/relatório/exceção. QoS de assinatura1: entregas dos loopbacks0/1/2
  são observadas0/1/1; isso NÃO atesta handshakeQoS2 MCU↔broker no wire.
- Após loopbacks, board assina control e publica retainedQoS1 seq3/4,1024bytes,
  espera PUBACK e sinaliza etapa. Host abre nova sessão, valida último replay
  RETAIN=1/QoS1/bytes exatos, publica controlQoS1 correspondente, encerra limpo.
- Board só avança após confirmação específica em MQTT, prazo15s; sem sleeps
  usados como prova. Após retained vazio/QoS1 e PUBACK, novo assinante deve
  não receber replay durante janela2s limitada; control5 confirma essa observação.
- Invariantes MQTT-3.3.1-5/6/8/9/10/11 confirmadas OASIS; zero byte não fica
  armazenado. Só laboratório/estado Docker novo por digest0.11.4, cleanup de
  recursos próprios; não editar firewall/roteador/rede/serviços reais.
- Parser fechado exige toda sequência adicional no modo retained; veto a
  FAIL/reboot/duplicata/missing/inválido. Positivo só se console E wire passarem.
  Não tratar ausência por timeout/TLS recusado como exclusão de retained.

## Aceite

Prompt apresentado antes de editar. Testes negativos wire/framing/bytes/flags/
identifiers/tetos/EOF/timeout, guards private/no-overwrite/ACL, sequência e
modo incorreto. Gates host, fmt, crossbuild release locked, Clippy e inventário;
teste físico COM4 com relatório sanitizado, ou falha real sem mascaramento.
Registro documenta limites: observador próprio independente do Rust, não
conformidade integral/negativos TLS/retained restart/Will/reconexão/heap/produção.

Atualizar checklist por capacidade realmente aprovada. Commit/push autorizados,
auditar segredo antes. Sem nova tag/deb/Hub para fixture-only: runtime não muda,
marcos publicados imutáveis. Distribuir novo runtime quando validado conforme
solicitação anterior. Não executar outras features automaticamente nesta fatia.

Fonte: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html#_Toc398718038

## Revisão v1.1 — antes de corrigir o teste adicional

Suíte inicial78executados/77PASS/1SKIP e gates do fixture PASS antes da gravação.
Dois negativos adicionais elevaram a suíte a80, mas um erro no double de teste
usou Mock sem spec para método cujo nome começa por assert_. Python o recusou;
não é evidência de falha no MQTT. Corrigir apenas o double para Mock(spec=Peer),
repetir80testes Windows e subset64 no WSL. Não alterar runtime por esse erro.
Ensaio físico já mostrou criação/update/delete no console; somente aceitar
após resultado final do runner+observer+cleanup e todos os testes aprovados.

## Revisão v1.2 — metadados e prova contra aprovação indevida

Primeiro ensaio PASS_RETAINED_SLICE com seis resultados wire e cleanup sem erros;
80testes Windows e64subset WSL aprovados. Revisão encontrou no relatório
privado rótulo P82 e lista remaining antiga, apesar do novo modo. Preservar
esse relatório histórico e corrigir somente metadados/finalização: promptP84,
pendências removidas apenas após console completo E observer completo.
Adicionar negativos contra console positivo sozinho e wire positivo/console
incompleto. Repetir ensaio com o mesmo firmware/certificados/backup, para gerar
novo relatório final correto; não sobrescrever evidência anterior. Isso não
altera broker/CLI/protocolo ou libera outro gateE01.
