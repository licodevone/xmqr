# P83 v1.1 — aplicar credenciais Wi-Fi corrigidas ao firmware E01

Base HEAD763ad245a16456d66bffa1e75631f73978e58210, broker/admin0.11.4,
client0.8.1 independente; main limpa. ESP32 na COM4, backup original4MiB
confirmado por duas leituras iguais. P82 coletor/40testes aceitos. Observação
posterior encontrou AP2,4GHz/WPA2, mas conexão expirou com motivo2.
O operador informou senha incorreta e alterou o arquivo privado indicado;
comparação booleana confirmou diferença da configuração compilada anterior.
Não imprimir ou versionar a senha. Windows mantém IP do endpoint de teste.

## Objetivo e escopo autorizado

Aplicar somente SSID/senha Wi-Fi do arquivo local já fornecido ao config privado
de build, recompilar, repetir gates e ensaiar firmware na COM4 conforme autorização
anterior de substituir por teste preservando backup. Sem solicitar senha no chat.
Corrigir cache: build.rs deve observar alterações do config/PEM privados.

Arquivos: validation/esp32-e01/{sync_wifi.py,test_sync_wifi.py,build.rs,README.md},
validation/esp32-e01/src/main.rs,
docs/{esp32-phase2-checklist.md,phase2-acceptance.md,evolution-plan.md,
plano-paridade-mosquitto.md,results/p83-e01-wifi-2026-10-13.json},
prompts/registros/P83-e01-wifi.md. Config runtime e produtos compilados só privados.

## Invariantes e migração

- Não alterar backend, CLI, dependências, quotas, versões, identidade MQTT,
  CA/certificados/chaves, políticas ACL ou formato durável. Fixture não é broker.
- Ler senha apenas do arquivo fonte privado. Validar UTF-8/SSID≤32bytes,
  senha WPA2 de8..63bytes ou64hex, sem caracteres de controle; preservar espaços
  legítimos, remover somente newline final. Não aceitar path escape/symlink externo.
- Target config deve ficar fora do Git, conter campos MQTT válidos; atualização
  atômica/exclusiva com backup privado único, preservando todos os outros campos.
  Sem reexecutar prepare_lab.py sobre certs existentes. Mesmos certificados do lab.
- Build Cargo privado C:/x81; adicionar rerun-if-changed para config/CA/leaf/key
  (somente paths em stdout, nunca conteúdo). Secrets/ELF/bin/backup jamais públicos.
- Backup completo conferido pelo runner antes de flash; bootloader/tabela SDK,
  verificação esptool, sem force/erase/NVS/efuses/GPIO. COM4 explícita.
- Broker de teste mTLS por digest, senha/fingerprint/ACL exclusivos já existentes,
  estado próprio/cleanup, sem firewall/roteador/serviços do operador ou fallback.
- Preservar arquivos e relatóriosP81/P82. Código próprio MIT e inventário intactos.

## Aceite e evidência

1. Prompt antes de mudanças; testes de atualização/noop e preservação TLS/MQTT,
   paths inválidos/insideGit, input inválido, backup e atomicidade.
2. Suíte Python do fixture, fmt, cross-build --locked --release, Clippy e inventário.
   Checar que generated config corresponde à senha corrigida somente por booleano.
3. Run físico com coletorP82: Wi-Fi/IP/SNTP/mTLS e bytes1024/QoS0/1/2, ou falha
   real identificada, sem extrapolar para todos os gatesE01 ou processamento de negócio.
4. Registro/relatório sanitizados e checklist com resultados reais. Sem fase3.

MQTT do backend/wire não é modificado; cláusulas de protocolo não mudam.
Mesmo PASS da primeira fatia não aprova retained/Will/reconexão/negativos/heap
ou observador independente. Tags/releases0.11.4/0.8.1 são imutáveis; não criar
pacotes novos para atualização de segredo privado. Commit/push de fontes/docs
validados estão autorizados, com auditoria antes do envio e limitações explícitas.

## Revisão v1.1 antes da correção de diagnóstico

Primeiro run com senha corrigida: flash verificado, mas scan isolado retornou
WIFI_TARGET_NOT_FOUND_24GHZ antes de testar autenticação; Windows imediatamente
viu o alvo/canal3. Não concluir ausência da rede ou erro da senha por esse scan.
Fonte esp-idf-svc0.53.0 inspecionada; filtro do scan passa ponteiro de String
ao SDK. Causa exata dessa divergência não foi demonstrada; não anunciar bug
de upstream nem alterar dependências/SDK/usar unsafe.

Retirar apenas o scan explícito como pré-condição. `wifi.connect()` do ESP-IDF
já faz scan do AP configurado, documentado oficialmente. Manter configuração
SSID/senha, observer, deadlines30s associação/30s IP, sem retry infinito ou
seleção de rede alternativa. Não ler/listar redes vizinhas na placa. Repetir
build/fmt/Clippy/suíte e ensaio isolado com mesmo backup/certificados/COM4.
Preservar resultado negativo anterior no registro; registrar nova tentativa
e sua falha ou sucesso real. Demais gatesE01 continuam abertos.

Fonte: https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32/api-guides/wifi.html#scan-in-wi-fi-connect
