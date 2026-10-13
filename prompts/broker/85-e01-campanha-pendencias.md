# P85 v1.2 — executar os testes físicos pendentes da fase2

Base0e42ee832029daf39e602c81218faa871d792100/main limpa, broker/admin0.11.4,
client0.8.1 intocado/tarballs preservados. P83/P84 positivos físicos aceitos
na COM4; backups originais4MiB iguais, firmware diagnóstico autorizado.
Pedido direto: seguir testes pendentes, não apenas explicar pendências.

## Escopo autorizado e limites

Uma campanha E01 supervisionada: Will por desconexão Wi-Fi da própria placa
sem MQTT DISCONNECT; reconexão finita; restart somente broker de laboratório;
retained antes/depois restart e delete; duplicataQoS1 sintética; cliente externo
Mosquitto2.0.22/QoS2; negativos CA/SAN/senha/ACL na placa; medição de memória.
Sem próxima fase/novas features core, router/firewall/rede do Windows/GPIO/
efuses/erase geral/NVS. COM4/backup/app≤1MiB verificados antes da gravação.

Arquivos validation/esp32-e01/{build.rs,sdkconfig.defaults,src/main.rs,
src/campaign.rs,src/memory_probe.rs,prepare_phase2.py,run_phase2.py,evidence.py,
test_phase2.py,test_evidence.py,README.md}; docs/{esp32-phase2-checklist.md,
phase2-acceptance.md,evolution-plan.md,plano-paridade-mosquitto.md,
results/p85-e01-campanha-2026-10-13.json}; prompts/registros/P85-e01-campanha.md.
Sem dependência nova/manifests/lock/versões/core/CLI. Código próprio MIT.

## Campanha e invariantes

- Modo opt-in XMQR_E01_CAMPAIGN=1, anteriores preservados. Firmware mantém
  CA/SAN/validade/clientcert/senha, TLSsemfallback, buffers2048/outbox8192.
- Novo caso privado exclusivo: reutilizar CA/board/observer vigentes; novo
  servidor SANIPdoendpoint+DNSe01-broker, perfil SAN errado apenas para negativo,
  CA não confiada e identidade externa distinta. Não sobrescrever originais.
  Docker mounts do broker não contêm chaves de CA/board/observer/cliente externo.
- Board pub bytes/retained/Will; sub bytes/control. Observer só publica control;
  externo só pub bytes/sub retained. Deny-by-default/filtros literais. Tópico
  proibido só para negativo, sem ampliar ACL para permiti-lo.
- Wi-Fi desconectada pela aplicação sem parar router/Windows: Will1024QoS1
  conferida por observer. Reconectar mesma rede em até3tentativas com backoff,
  tempos registrados, bytes1KiB após recuperação. Não afirmar corte de energia.
- Broker próprio restart com mesmo volume; recuperar MQTT em até3tentativas,
  revalidar retained1024/replay e delete. DuplicataQoS1 induzida pelo publisher
  fixture (DUP/ID), sem prometer exatamente-uma-vez de negócio ou perda real de rede.
- Mosquitto2.0.22 oficial existente por digest: sub replayQoS2/bytes exatos e
  pubQoS2 para MCU com bytes conferidos. Senhas só em configs privados/default
  XDG, não argv/env/log público. Não equivale a captura descriptografada do TLS.
- SAN coordenado: confirmaçãoMQTT30 e markerARMED antes da troca; MCU espera8s,
  host exige troca/precheck≤6s e ACKcontrole≤1s, senão FAIL_COORDINATION.
- Negativos com baseline positiva, falha do cliente observada e serviço vivo:
  CA desconhecida, senha errada, publish sem ACL, SAN errado. Não aceitar simples
  silêncio/timeout como recusa. Confirmar caminho válido novamente; preservar
  verificações, sem insecure. CallbackSDK tem erro genérico: não inventar códigos
  TLS detalhados que API segura não oferece.
- Memória: Vec.try_reserve_exact, uma alocação por vez, passos4096/teto196608,
  SDKabort-on-allocation-fail desabilitado. Registrar maior probe aprovada em
  checkpoints comparáveis e outbox; isso mede capacidade contígua aproximada,
  não heap total/min/largest estatístico exato nem ausência de vazamento longo.
  Sem unsafe/FFI nova. Gate curto exige capacidade mínima8192 e queda≤32768.
- Parser fechado, ordem e limites512bytes/64KiB/128markers/180s; callbacks de
  teste têm prazos finitos. Relatórios únicos, limpeza de container/volume/rede
  e jobs somente próprios, mesmo após falha. Não aprovar só pelo console.

## Aceite/registro/publicação

Prompt apresentado antes das mudanças. Unitários negativos do host/parser/
guards e probe puroRust no host; cross-build/fmt/Clippy para modos usados,
inventário146licenças preservado; placa real com provas wire/cliente terceiro
e métricas ou falha real. Classificar gates individualmente PASS/FAIL/NOT_RUN.
Aceitar fase2 só após cobrir checklist original e softwareP80/C43; limitações
adicionais não viram promessa de conformidade integral/produção. Não inflar
novos pré-requisitos por exigir pcapTLS/attestation não previstos no gate.

Commit/push autorizados após auditoria de segredos. Se só fixture/docs mudarem,
não retag/republicar runtime0.11.4/0.8.1. Distribuição .deb/Docker já publicada
permanece; novos marcos de runtime exigem gates do commit e pacotes próprios.
Sem upload de firmware/ELF/config/keys/backups com credenciais. Registrar SHAreal.

Normas: OASIS3.1.1 §3.1.2.5/§3.3.1.3/§4.3.2/§4.3.3, especialmente
MQTT-3.1.2-8, MQTT-3.3.1-5/6/8/9/10/11. Confirmação de ensaio não é negócio.

## Revisão v1.1 — execução dos gates

Primeira chamada unittest usou start directory relativo à raiz, mas cwd estava
no próprio fixture; falhou antes de importar/executar testes. Corrigir somente
invocação para discovery `-s .` no fixture, sem mudar fontes por esse erro.
Repetir gates antes de flash. Controle retido8/31 coordena assinatura após
restart/restauração; estágioSAN usa confirmação30/ARMED e orçamento declarado.

## Fechamento/publicação da evidência

Campanha real PASS com14provas wire/externas,0violações/cleanup, memória/probe
110592 em quatro checkpoints, recuperaçãoWi-Fi9048ms/broker7869ms. 94testes
Windows/1SKIP e94WSL/0SKIP;2Rustprobe; builds/Clippy modo anterior e campanha.
Combinar com softwareP80/C43 e runtime idêntico às tags para aceite fase2.
Alinhar client por C44 separado. Limitações adicionais (heap total exato,
campanha longa, energia/pcapTLS) permanecem explícitas, não gates inventados.

Após auditoria/commit/push, anexar SOMENTE JSONsanitizado P85 às releases
existentes0.11.4/0.8.1 e atualizar notas com adendo do aceite + link do commit.
Não clobber arquivo existente diferente; não mudar tags/pacotes/digests/latest
ou fabricar versão nova sem mudança de runtime. Verificar novos assets remotos.
