# P83 — senha corrigida e primeira comunicação física ESP32

2026-10-13, base763ad245a16456d66bffa1e75631f73978e58210, main limpa;
broker/admin0.11.4 e client0.8.1 independente. Autorização anterior de ensaio
com backup/gravação na COM4 e commit/push preservada. Tarballs preexistentes
do client intocados. [PromptP83v1.1](../broker/83-e01-atualizar-wifi.md),
criado antes da implementação; revisãov1.1 antes da correção após falha real.

Skills xmqr-rust-mqtt/tests/security-review aplicadas pelo agente principal,
sem subagentes. Guiaram limites, testes negativos e proteção dos segredos.
Não alterou núcleo broker/admin, CLI, dependências, quotas, licenças ou versões.

## Mudanças

- sync_wifi.py: lê somente arquivos privados fora do Git; SSID UTF-8≤32bytes,
  senha8..63bytes ou64hex; não remove espaços legítimos. Recusa controles,
  entradas>64KiB, escape de path e resolução/symlink externo. Sem argumentos
  com senha ou detalhes sensíveis em falhas. Noop não reescreve config.
- Backup privado único/exclusivo e troca atômica do JSON; preserva campos
  MQTT e extras. Recusa alteração concorrente detectada antes da troca;
  essa comparação não é lock entre processos nem garantia contra atacante
  capaz de modificar diretório privado durante a operação.
- build.rs observa JSON/CA/leaf/key privados; constants/target/ELF/bin só no
  diretório privado. Não regenerou CA/certificado/chaves/ACL nem alterou EIM.
- Firmware não exige scan diagnóstico separado. SDK `wifi.connect()` procura
  somente o AP configurado, associação30s/IP30s, sem rede alternativa ou retry
  infinito. Não alterou SDK/dependências nem acrescentou unsafe.

## Evidência real

| Verificação | Resultado |
| --- | --- |
| Primeiro unittest com Python comum | Falhou importando pyserial ausente; sem instalar nada, usado venv ESP-IDF existente |
| Suíte Windows final |55executados/54PASS/1SKIP, saída0; host não pode criar symlink real |
| Sync isolado WSLUbuntu26 |15PASS/0SKIP, saída0, incluindo symlink real; dados sintéticos |
| Fmt/cross-build release locked/Clippy -D warnings | PASS antes de cada gravação |
| Inventário Cargo fixture | PASS,146declarações, dependências intactas; MIT próprio não relicencia SDK/terceiros |
| Sincronização privada | config difere da anterior; depois igual à fonte corrigida; campos não Wi-Fi preservados |
| Constants geradas/Cargo watch | booleanosTRUE; sem imprimir senha ou chave |
| Backups | duas leituras4MiB iguais; hash no JSON; conferidas antes de ambas gravações |
| Primeira tentativa | Flash verificado; scan isolado sem alvo; FAIL_INITIAL_SLICE, saída1 |
| Consulta Windows imediata | alvo visível/canal3; scan da placa não prova ausência da rede |
| Segunda tentativa | Flash verificado; Wi-Fi/IP → SNTP → mTLS → bytes1024/QoS0/1/2 → PASS_INITIAL_SLICE → STOP; saída0 |
| Coletor segunda tentativa |0violações,617bytes lidos,12linhas descartadas sem conteúdo |
| Cleanup |0erros nas duas tentativas; container/volume próprios ausentes após execução |

Dados/timestamps UTC e ambas tentativas no
[relatório sanitizado](../../docs/results/p83-e01-wifi-2026-10-13.json).
O disconnect após os três loopbacks ocorre no `wifi.stop()` explícito do
encerramento; não foi cenário de queda/reconexão. Broker de teste mTLS0.11.4
por digest379439bd82f03c6c237d1e1f2f9a452e20fa62e24538200b97a06af6dae394bd,
certificado exclusivo + usuário/senha + ACL mínima já preparados. Host verificou
CA/SAN/certificado antes de gravar; placa manteve verificação TLS habilitada.

Consulta a fonte esp-idf-svc0.53.0 local e documentação oficial confirmou
que connect faz scan do AP configurado. Remover pré-scan permitiu avançar;
isso não prova causa exata da divergência anterior nem bug upstream.
[ESP-IDF5.5.5](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32/api-guides/wifi.html#scan-in-wi-fi-connect)
e [esp-idf-svc](https://github.com/esp-rs/esp-idf-svc/blob/master/src/wifi.rs).

## Limites e entrega

PASS somente primeira fatia física positiva e atualização privada. Ainda
NOT_RUN: retained/Will/reconexão/negativos físicos/heap/observador independente.
Console não prova wire nem resultado de negócio; source_sha256 é hash das
fontes do host, não vínculo criptográfico ELF↔Git. Sem fase3/produção/aceite
globalE01. Gates111Rust broker/54Rust client anteriores não repetidos porque
seus núcleos/manifests não mudaram; build/clippy do fixture foram repetidos.

Senha Wi-Fi/MQTT, certificados privados, backup flash, JSON/ELF/bin/target e
logs completos não serão públicos. Nenhum firewall/roteador/serviço real/NVS/
efuse/GPIO alterado; não houve erase geral. Firmware diagnóstico fica na placa;
ele não mantém sessão MQTT após STOP. Laboratório não mantém broker ativo.
Registros privados anteriores preservados; também criado backup privado do
JSON anterior, com segredos, não publicável.

Sem nova tag/release/deb/Hub porque runtime0.11.4/0.8.1 não mudou; releases
existentes imutáveis e compromisso de distribuir próximo marco preservado.
Commit/push de fonte/prompt/docs sanitizados autorizados após auditoria.
SHA real do commit será confirmado na entrega, não previsto neste registro.
