# E01 — cliente físico de validação ESP32

Pacote Rust independente, código próprio MIT. Não faz parte do crate do broker,
não instala XMQR na placa e não substitui o aplicativo consumidor mqtt-broker.
Alvo observado: ESP32 DevKitV1/ESP32-D0WD-V3/4MiB/COM4.

AtualP85/2026-10-13: campanha curta E01 ACCEPTED junto a softwareP80/C43.
Will/quebra de link, reconexãoWi-Fi/broker, retained após restart/live/delete,
duplicataQoS1, Mosquitto2.0.22/QoS2 e negativosCA/senha/ACL/SAN PASS.
Probe contíguo Rust110592bytes estável em quatro checkpoints; Wi-Fi9048ms/
broker7869ms. Não são estatísticas exatas do heap, prova de vazamento longo,
energia, pcapTLS ou produção. [RegistroP85](../../prompts/registros/P85-e01-campanha.md).

P84 amplia o ensaio com retained e observador wire Python independente do
codec Rust/SDK, certificado e usuário próprios. Não é libmosquitto nem prova
integral de protocolo: a assinaturaQoS1 observa os loopbacks como0/1/1 no
wire e não captura o handshakeQoS2 da placa. Interop MosquittoC43 é separada.
Veja [registroP84](../../prompts/registros/P84-e01-retained.md).

CheckpointP83/2026-10-13: primeira fatia física PASS: Wi-Fi/IP, SNTP, conexão
MQTT3.1.1 mTLS e loopback sintético1024bytes/QoS0/1/2. Senha corrigida aplicada
privadamente, firmware regravado com backup conferido. Scan diagnóstico não
é mais pré-condição; ESP-IDF conecta somente ao AP configurado. Sem rede
alternativa, insegurança TLS ou retry ilimitado. Container/volume de teste
removidos; firmware diagnóstico fica na placa. E01 completo ainda PARTIAL.
[RegistroP83](../../prompts/registros/P83-e01-wifi.md). Checkpoints abaixo são históricos.

P82/2026-10-13: coletor fechado e40testes do host PASS; monitor-only real
confirmou boot/erro de alvo Wi-Fi2,4GHz ausente/STOP, sem nova gravação.
MQTT físico continua NOT_RUN. [RegistroP82](../../prompts/registros/P82-e01-coleta.md).

CheckpointP81: build/fmt/Clippy, inventário e8testes dos guards PASS;
duas leituras do backup iguais; duas gravações verificadas e boots reais.
Wi-Fi falhou: scan do alvo em2,4GHz não o encontrou. Windows também não
apresentou correspondência. SNTP/MQTT da placa NOT_RUN; senha não avaliada.
Veja [registroP81](../../prompts/registros/P81-esp32-e01.md).

## Primeira fatia

Wi-Fi com prazo, SNTP antes do TLS, MQTT3.1.1 com CA/SAN/validade, certificado
exclusivo, usuário/senha e ACL mínima. Auto-loopback sintético1024bytes com
sequência por QoS0/1/2. Filas/buffers finitos; reconexão automática desabilitada
nesta primeira fatia. Erros exibem somente nome fixo da etapa.

Isso não aprova todoE01: retained, Will, falhas/reconexão, negativos físicos,
heap e confirmação por observador independente ainda exigem testes próprios.
`E01_INITIAL_SLICE_PASS` não significa fase2 concluída ou produção aprovada.

## Preparar sem expor credenciais

1. Leia [P81](../../prompts/broker/81-esp32-e01-fisico.md). Confirme COM/chip.
2. Faça duas leituras completas4MiB para arquivos privados diferentes; compare
   tamanho/SHA256. Sem backup consistente, **não grave**. Não publique o backup.
3. Use pasta privada fora do Git com ACL usuário/SYSTEM/Administradores.
   `wifi-config.json`: campos `ssid`, `serial_port`, `password_file`.
   A senha fica no arquivo apontado, UTF-8, uma linha, nunca em argumento.
4. Execute `prepare_lab.py --private-dir DIRETORIO --endpoint IP_DO_HOST`
   em Python existente. Requer OpenSSL, WSLUbuntu26 e admin0.11.4 compilado
   no mesmo repositório; não instala ferramentas nem inicia broker.
5. Compile com `build-windows.ps1 -PrivateDirectory DIRETORIO_PRIVADO`.
   O ambiente Python ESP-IDF deve funcionar; ajuste parâmetros dos caminhos
   ao computador. O script não seleciona EIM globalmente nem grava a placa.
   Windows exige saída curta (ex.: diretório novo privado `C:/x81`).
6. Após gates, inicie apenas broker de teste mTLS com CA/usuários/ACL novos,
   estado próprio e bind no IP LAN específico. Não alterar firewall/serviços.
7. Gravação/monitor somente após backup conferido, binário compilado e alvo
   confirmado. Sem GPIO, efuses ou erase-flash geral. Registre resultados reais.

O runner `run_initial.py --private-dir DIR_BUILD --backup-dir DIR_BACKUP`
faz apenas pré-check host. `--flash` substitui o firmware e executa o ensaio:
requer esptool/pyserial existentes, backupsP81 com nomes conferidos no script,
app até1MiB e COM correta. Usa imagem0.11.4 por digest, estado próprio,
bootloader/tabela reais do SDK e verificação da gravação. Não apaga NVS;
o firmware não inicializa NVS/calibração persistente. Container/volume de teste
são removidos no fim; firmware diagnóstico fica na placa. Não há broker
permanente ativo depois do runner. Não execute --flash por mera leitura.

## Observar sem regravar — P82

Execute no ambiente Python existente com pyserial:

```text
python run_initial.py --private-dir DIRETORIO_PRIVADO --serial-port COM4 --monitor-only --seconds 40
```

Esse modo abre a serial e faz reset normal para observar o firmware existente;
não grava flash, cria Docker, gera credenciais ou altera rede/firewall.
`--monitor-only` e `--flash` são mutuamente exclusivos. Confirme o alvo antes
de executar; reset pode interromper um aplicativo em uso.

Somente formatos conhecidos podem ser exibidos/guardados. ASCII estrito,
newline completo e ordem de milestones são obrigatórios. Erro, reboot,
duplicata de milestone, timeout ou limite excedido impedem aprovação. Tetos:
512bytes/linha,64KiB lidos,128markers, prazo1..180s e cauda pós-STOP até1s,
sempre dentro do prazo global. Linhas desconhecidas não são copiadas para logs.

Relatórios schema2 são salvos em novos `e01-result-DATA-UUID.json` privados,
sem sobrescrever `initial-result.json` ou relatóriosP81. Erro de gravação do
relatório não impede tentativas de limpeza dos recursos de laboratório criados
pelo runner; falha de cleanup é FAIL_CLEANUP, com códigos fixos, sem stderr bruto.

Mesmo uma sequência aparentemente positiva no monitor-only resulta em
OBSERVED_MARKERS_ONLY, não PASS: console não atesta identidade/fonte do firmware
instalado nem wire MQTT. Testes sintéticos do coletor não são MQTT físico.
O modo --flash preserva os requisitos de backup e apenas usa o novo coletor.

## Corrigir a senha já preparada — P83

Alterar `wifi-password.txt` não muda o firmware instalado. Para sincronizar
somente SSID/senha no diretório privado de build existente:

```text
python sync_wifi.py --source-dir DIRETORIO_WIFI_PRIVADO --private-dir DIRETORIO_BUILD_PRIVADO
```

O helper não imprime credenciais. Recusa caminhos externos/Git e senha WPA2
inválida; preserva espaços legítimos e remove somente CR/LF finais. Antes da
troca atômica, salva backup privado exclusivo da configuração anterior. MQTT,
CA, certificado da placa, chave e ACL não são regenerados. Não publique os
backups JSON: também contêm segredos. Sem alteração, não reescreve arquivos.

Depois recompile, repita fmt/Clippy e confira os backups completos antes de
executar `run_initial.py --flash`. O build observa mudanças do JSON e dos três
PEMs privados para não reutilizar constantes antigas em cache. O helper não
grava a placa nem inicia serviços. Testes do host usam dados sintéticos.

## Retained com confirmação externa — P84

Sobre laboratório privado já preparado, crie uma vez a identidade separada:

```text
python prepare_retained.py --private-dir DIRETORIO_BUILD_PRIVADO
```

Recusa config já existente/Git; cria pasta privada nova, sem alterar originais.
CA/servidor/board do lab são preservados. Observer ganha certificado válido3dias,
usuário/senha e fingerprint próprios; broker recebe só certificados públicos,
sua própria chave e políticas, não chaves de CA/dispositivo/observer.
Os certificados ainda precisam estar dentro da validade da CA do laboratório.

No PowerShell do build (ambiente local ao processo; não usar setx):

```powershell
$env:XMQR_E01_RETAINED = '1'
./build-windows.ps1 -PrivateDirectory DIRETORIO_BUILD_PRIVADO
```

Após testes/fmt/Clippy/backups/chip/COM conferidos, o ensaio explicitamente
autorizado usa o Python existente com esptool/pyserial:

```text
python run_initial.py --private-dir DIRETORIO_BUILD_PRIVADO --backup-dir DIRETORIO_BACKUP_PRIVADO --serial-port COM4 --retained --flash
```

Isso substitui firmware diagnóstico: não executar por mera leitura. Sem flag
--flash, faz só pré-check host; --monitor-only observa/reset sem gravar e não
aprova wire/identidade. Para o modo inicial anterior, compile com variável0 e
rode sem --retained. Não misture modo do firmware/coletor: sequência incompleta
ou modo errado veta PASS. Produtos compilados continuam privados, não publicáveis.

Após loopbacks, a placa publica retainedQoS1 com1024bytes seq3/4. A cada etapa,
observer abre sessão nova e exige RETAIN=1/QoS1/bytes do último valor, antes de
confirmar pelo tópico de controle exclusivo. Placa espera essa confirmação15s.
Publicação retained vazia apaga o valor; novo subscriber não recebe replay por
janela2s e responde a PING antes de confirmar exclusão. EOF/falhaTLS/ACK incorreto
não contam como ausência. Não é prova de retenção após restart ou longa duração.

Observer limita pacote4096,32frames/ACK, fila32, IDs/deadlines e usa CA/SAN.
Console tem parser fechado/tetos anteriores e sequência adicional obrigatória.
Somente console completo E seis resultados wire completos permitem
PASS_RETAINED_SLICE; isso não conclui fase2/negativos TLS/Will/reconexão/heap.
Confirmação é evidência de ensaio, não sucesso de negócio ou attestation ELF↔Git.
Os dois participantes se encerram, container/volume próprios são removidos e
firmware diagnóstico fica na placa; não há broker permanente do teste.

## Campanha dos gates restantes — P85

Requer laboratórioP84 privado válido e imagens existentes pinadas. Prepare
uma vez o novo caso, sem sobrescrever os anteriores:

```text
python prepare_phase2.py --private-dir DIRETORIO_BUILD_PRIVADO
```

Cria servidor com SANIP+DNSdo laboratório, perfil SAN errado separado, CA
desconhecida e identidadeMosquitto exclusiva. Board/observer/CA originais
preservados; nenhuma chave de dispositivo/CA vai para mount do broker.
ConfigsMosquitto ficam privados, lidos por XDG_CONFIG_HOME; não há senha em argv.

No PowerShell do build, processo local:

```powershell
$env:XMQR_E01_CAMPAIGN = '1'
$env:XMQR_E01_RETAINED = '0'
./build-windows.ps1 -PrivateDirectory DIRETORIO_BUILD_PRIVADO
```

Após gates e confirmação dos dois backups/chip/COM:

```text
python run_phase2.py --private-dir DIRETORIO_BUILD_PRIVADO --backup-dir DIRETORIO_BACKUP_PRIVADO --serial-port COM4 --flash
```

Grava firmware diagnóstico e provoca desconexão somente da própria placa;
reinicia/substitui somente broker temporário e seus perfis/certificados de
teste. Recurso existente é recusado, não removido. Sem firewall/roteador/GPIO,
efuse/erase geral ou NVS. Mosquitto é cliente terceiro real, não simulador de ESP.
Ctrl8/31 retidos coordenam assinaturas após restart/restauração; Ctrl30/ARMED
coordena SAN, com prazo de troca verificado. Loops de reconexão têm3tentativas
e backoff1/2/4s. Negativos exigem erro/desconexão observados + baseline/caminho
válido recuperado; callbackSDK não expõe códigoTLS exato, não o inventar.

Memória: uma Vec.try_reserve_exact por vez, passos4096/teto196608, sem unsafe.
SDKabort-on-allocation-fail desabilitado/conferido. Mede capacidade contígua
aproximada, não total/min livre. Gate curto: probe≥8192, quedaidle→final≤32768,
outbox0, recuperação≤60000ms. Não promete SLA nem ausência de vazamento longo.

Parser fechado/180s/64KiB/128markers e14provas externas + métricas necessários
para PASS_PHYSICAL_CAMPAIGN. Runner isolado sempre mantém phase2_closed=false:
o aceite global é decisão documental que combina esses gates com P80/C43,
não apenas o console. JSON único/privado, cleanup de jobs/container/volume/rede
somente próprios. Firmware diagnóstico fica instalado e se encerra no STOP.

Os certificados temporários duram5dias; regenere em nova pasta para repetir.
ELF/bin/target e `firmware-config.json` contêm senha/chave: não publicar, mesmo
que o nome do arquivo pareça um artefato comum. O build recusa saída fora da
pasta privada. O backup continua privado mesmo após remover dados Wi-Fi atuais.

## Recuperação

Preserve ambos backups e hashes. Para restaurar, confirme mesmo chip/COM e
use espflash write-bin no endereço0 com o backup completo, sem `--force`.
Restaurar reintroduz configurações/credenciais originais. Não executar comandos
de restauração por mera leitura deste documento.

## Fontes e licenças

- [esp-idf-svc](https://github.com/esp-rs/esp-idf-svc): MIT OR Apache-2.0.
- [esp-idf-sys/build](https://github.com/esp-rs/esp-idf-sys/blob/master/BUILD-OPTIONS.md).
- [Rust/ESP-IDF](https://docs.esp-rs.org/book/).
- [ESP-IDF5.5.5](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32/):
  preserve licenças do SDK e componentes; MIT do fixture não as substitui.
- [EIM](https://docs.espressif.com/projects/idf-im-ui/en/latest/).
- [espflash](https://github.com/esp-rs/espflash).
- [OASIS MQTT3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html).

O Cargo.lock local fixa o grafo deste fixture; o inventário/licenças do broker
permanece separado. Não afirmar que toda dependência tem licença MIT.
