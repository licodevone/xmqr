# P81 v1.11 — validação física E01 em Rust/ESP-IDF

Estado de entrada: broker/admin0.11.4, HEADd2928f03e157aeb44adb01801d0a459a6a940103;
cliente independente0.8.1, HEAD6495f9dd59475e90612b9055723c374a4d0df725.
Fase2 tem gates de software aprovados por P80/C43 e E01 físico pendente.
ESP32 DevKitV1 identificado na COM4, ESP32rev3.0/flash4MiB.
O mantenedor autorizou preservar o firmware atual e substituir por teste.
Credenciais Wi-Fi fornecidas em arquivo privado, fora dos repositórios.

## Objetivo e escopo

Executar backup verificável antes de gravar; preparar cliente de validação
Rust/ESP-IDF separado do núcleo; observar MQTT3.1.1 com XMQR e preencher
somente resultados reais do checklistE01. Não instalar o broker na placa.

Arquivos previstos: validation/esp32-e01 (pacote Cargo independente, scripts,
README, configuração sem segredos), docs/esp32-phase2-checklist.md,
docs/phase2-acceptance.md e prompts/registros/P81-esp32-e01.md.
Revisar este prompt antes de correções após falhas. Manter execução incremental.

## Proteções e compatibilidade

- Ler flash4MiB a partir de0, sem erase/write, para pasta local privada.
  Conferir tamanho/SHA256 e segunda leitura antes de qualquer gravação.
  Backup pode conter credenciais antigas: não exibir, versionar ou publicar.
- Sem GPIO, relés ou pinagem presumida; não alterar efuses/secureboot/partições
  sem necessidade documentada. Se o backup falhar, não gravar.
- Credenciais, chaves, certificados, estado e produtos compilados com segredos
  ficam na pasta privada do operador, nunca no Git/artefatos da release.
- Reutilizar ferramentas existentes; verificar ESP-IDF/EIM/Rust e ambientes
  Python. Dependência indisponível é BLOCKED, não instalar por mera leitura.
- Usar apenas instância de teste, mTLS, usuário/senha exclusivos e ACL mínima.
  Sem insecure, fallback plaintext ou desativar validação CA/SAN/validade.
  Esperar SNTP com prazo antes de TLS. MQTTclientIDs separados da CLI.
- Não alterar firewall, conexão Wi-Fi do Windows, serviço do operador ou clone
  WSL. Se acesso LAN for bloqueado, registrar evidência e não burlar controles.
- Não alterar núcleo, quotas, formato durável ou versões0.11.4/0.8.1.
  Ferramenta de validação não entra no Cargo.lock/dependências do broker.
  Código próprio MIT; inventariar licenças das dependências do fixture.

## Fatias e aceite

1. Prompt, pré-requisitos e backup verificável; registrar chip/porta/ferramentas.
2. Firmware compilável com credenciais externas, logs sanitizados, filas e
   prazos limitados; fmt/check/Clippy e inventário do pacote independente.
3. Gravar somente após1/2; observar boot/heap/Wi-Fi/SNTP/mTLS e pub/sub bytes.
4. Executar QoS0/1/2 conforme suporte comprovado, retained replay/update/delete,
   Will por reset/link, reconexão Wi-Fi/restartbroker e CA/SAN/senha/ACL negativos.
5. Evidência PASS/FAIL/BLOCKED/NOT_RUN por cenário; atualizar gate sem assumir
   que ACK equivale a processamento de negócio ou sessão a persistência da placa.

Os requisitos MQTT seguem OASIS3.1.1 §§3.1,3.3–3.9,3.14,4.3–4.4.
Sem mudança de wire do XMQR, conformidade integral ou avanço para fase3.
Publicar somente fontes/documentação sanitizadas após validação pertinente;
commit/push estão autorizados na conversa. Tags existentes são imutáveis;
não criar nova release de runtime apenas para evidência documental.

## Recuperação

Preservar backup privado com tamanho/hash e instrução espflash write-bin
para mesmo alvo COM4/chipESP32/endereço0. Restaurar somente se necessário
e dentro do escopo autorizado; jamais publicar o binário com credenciais.

Referências: [E01](../../docs/esp32-phase2-checklist.md),
[aceite fase2](../../docs/phase2-acceptance.md),
[ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32/),
[esp-idf-svc](https://github.com/esp-rs/esp-idf-svc),
[espflash](https://github.com/esp-rs/espflash).

## Revisão v1.1 após pré-requisitos/backup

Primeira leitura espflash460800 falhou com pacote truncado (1000/5ea hex);
não há backup aprovado nem autorização para gravar sem ele. Repetir em arquivo
novo, baud115200, blocos1024 e max-in-flight1, prazo15min por leitura.
Manter arquivo parcial privado, sem tratá-lo como recuperável.
Ambos os venvESP-IDF5.5.5/6.1 apontam para Python3.14 ausente; Python3.13 e
runtime3.12 existentes não substituem módulos nativos cp314. Verificar alternativas
existentes; não alterar venv/EIM ou instalar dependências globalmente em silêncio.

## Revisão v1.2 — alternativa existente

Segunda leitura espflash115200 também falhou (timeout), ambos arquivos0bytes.
Foi encontrado venv já instalado idf5.5_py3.13_env: imports serial/esptool/
idf_component_manager PASS e idf.py --version retorna ESP-IDFv5.5.5.
Reutilizar esse ambiente apenas no processo de build/teste, sem mudar seleção
global EIM. Tentar backup esptool4.12.0 já instalado, baud115200/prazo15min,
arquivo novo. Segunda cópia independente deve validar SHA256 antes de gravar.

## Revisão v1.3 — primeira fatia de firmware

Separar o primeiro build/ensaio Wi-Fi/SNTP/mTLS/pub-sub1024bytes do restante
deE01. Inicialmente retained/Will/reconexão/negativos/heap ficam NOT_RUN,
nunca aprovados por auto-loopback. Credenciais geradas por script só produzem
arquivos na pasta privada; hashArgon2 pelo admin existente no WSL/PTY.
Reutilizar ambiente ESP-IDFfromenv; fmt e lockfile do fixture separados.
Configurar raiz Cargo explicitamente para o target privado. Não usar auto-
instalação ESP-IDF/PlatformIO nem instalar Python globalmente.

## Revisão v1.4 — build Windows

Primeiro build chegou ao esp-idf-sys, mas não encontrou idf.py no PATH;
também detectou saída longa pela redireção AppData do aplicativo Windows.
Adicionar somente PATH do processo com tools/idf.py e idf-exe existentes.
Preparar C:/x81 como diretório novo privado de build (se não existir), com
ACL somente usuário/SYSTEM/Administradores; copiar configuração/certificados
privados, nunca backup ou segredos para Git. Não usar subst/WSL clone antigo.
Trocar espera de startWi-Fi por polling limitado e usar sequência nos bytes
para não confundir duplicata QoS1 com confirmação de outra mensagem.

## Revisão v1.5 — componente de entrada SDK

O SDK compilou bibliotecas, mas link libespidf falhou por app_main ausente:
a lista reduzida de componentes excluiu main gerado pelo esp-idf-sys.
Incluir main explicitamente e repetir build isolado, sem alterar SDK instalado.
Backup esptool foi confirmado por duas leituras independentes4MiB com SHA256
idêntico. Permanecem gates de build/Clippy/segurança antes da primeira gravação.

## Revisão v1.6 — busca de DLL no processo

Componente main resolveu o link SDK. Bindgen não carregou libclang.dll;
diagnóstico WinDLL com busca padrão reproduziu falha e passou ao incluir
o diretório esp-clang/bin no PATH. Acrescentar esse diretório no processo
de build; nenhuma DLL/ferramenta precisa ser instalada ou alterada globalmente.

## Revisão v1.7 — bindings HAL

Busca DLL resolvida. Bindgen requer driver/periph_ctrl.h do componente driver
do SDK5.5.5, ausente da lista reduzida. Incluir driver, manter SDKfromenv,
sem copiar/patchar cabeçalhos instalados. Runner físico deve comparar backups,
checar broker mTLS antes de flash, usar bootloader/partitiontable do build SDK
e esptool com verificação, sem erase da NVS ou flash inteira. Somente logs
E01 conhecidos; limpar container/volume exclusivos ao término, nunca recursos
preexistentes. Sem argumento --flash o runner faz apenas pré-check do host.

## Revisão v1.8 — dependências SDK e preservação NVS

Driver/bindings passaram; esp-idf-svc0.53.0 requer símbolos dos componentes
spiffs/fatfs/wear_levelling mesmo sem uso de filesystem pelo fixture.
Incluir esses componentes sem mudar SDK instalado nem dependências do broker.
Revisão da API EspDefaultNvsPartition::take encontrou fallback que pode apagar
NVS em erro de versão/espaço. Evitar inicialização NVS e passar None ao Wi-Fi;
desabilitar armazenamento NVS Wi-Fi/calibração PHY. Não ler/migrar dados
do firmware anterior. Adicionar testes para backups ausentes/parciais/divergentes.

## Revisão v1.9 — aceites e recursos exclusivos

Exigir evento Published do SDK para QoS1/2 além da volta dos bytes/seq, antes
do teardown, sem confundir ACK com processamento de negócio. Criar container
separadamente de start para registrar ownership e limpar mesmo após falha
de inicialização. Nunca remover container/volume preexistente; rejeitar colisões.
Inventário Cargo: registrar licenças declaradas, sem reclassificá-las como MIT
ou equiparar inventário a auditoria completa de SDK/firmware de produção.

## Revisão v1.10 — diagnóstico físico Wi-Fi

Build/fmt/Clippy/inventário e8testes dos guards PASS. Pré-check mTLS do host
PASS; primeira gravação esptool verificada e boot real observado. A placa
falhou WIFI_IP_TIMEOUT, portanto SNTP/MQTT continuam NOT_RUN.
Adicionar scan somente do SSID já fornecido, limite15s/até4resultados, sem
imprimir SSID/BSSID/senha; registrar presença/canal/RSSI/tipo de autenticação
e motivo numérico de desconexão. Observar associação separada de DHCP.
Não escolher outra rede, trocar senha, configurar roteador ou enfraquecer
autenticação. Preservar relatório desta tentativa antes de repetir; uma
segunda gravação só com build/gates repetidos e mesmo backup aprovado.

## Revisão v1.11 — evidência e parada por rede indisponível

Segunda gravação/boot verificados; scan físico não encontrou o alvo2,4GHz.
Consulta Windows retornou zero correspondências exatas ou sem diferenciar
maiúsculas para o alvo. SSID e transferência da senha foram conferidos apenas
por booleanos, sem imprimir conteúdo. Não atribuir falha à senha: autenticação
Wi-Fi não foi alcançada. Manter firmware diagnóstico na placa, backups privados
e nenhum serviço de teste permanente. Não tentar rede alternativa ou alterar
roteador/firewall. Atualizar também evolução/plano de paridade com estado real,
versionar relatório sanitizado, README/ignores/licença do fixture e registro.
Commit/push apenas fontes/docs aprovados pelos gates; sem nova tag/release.
