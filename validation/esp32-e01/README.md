# E01 — cliente físico de validação ESP32

Pacote Rust independente, código próprio MIT. Não faz parte do crate do broker,
não instala XMQR na placa e não substitui o aplicativo consumidor mqtt-broker.
Alvo observado: ESP32 DevKitV1/ESP32-D0WD-V3/4MiB/COM4.

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
