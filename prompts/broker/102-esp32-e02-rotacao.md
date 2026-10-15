# P102 rev1 — E02: campanha física de rotação na COM4

2026-10-15. Entrada: P100/B11 e P101/B09 integrados em laboratório Ubuntu26;
ESP32 DevKit V1/CH340 presente na COM4 por confirmação do mantenedor. Backup
original do alvo, duas leituras de 4 MiB com mesmo hash, é pré-condição para
qualquer gravação. Não usar estado/serviço MQTT real, nem expor Wi-Fi, senhas,
chaves, hashes, payloads ou MAC em logs/commits.

Objetivo: firmware diagnóstico opt-in E02 (exclusivo de E01) com etapas finitas
de conexão mTLS, derrubada voluntária da própria sessão e tentativa nova após
cada sinal. Host inicia broker P100 isolado em Docker/porta de laboratório,
prepara certificados e CRLs privados, observa marcadores fechados da UART e
alterna arquivos TLS + SIGUSR1 com confirmação do evento de publicação/recusa.

Casos: baseline, chave inválida recusa reload e mantém confiança antiga;
certificado novo assinado pela CA existente aceita; certificado de CA estranha
é publicado mas a placa recusa novo handshake; rollback restaura conexão;
CRL assinada pela CA original revoga o certificado da placa e recusa novo
handshake; CRL limpa restaura. Cada negativo exige evento de erro/desconexão
observado, sem afirmar código TLS não exposto pelo SDK. As conexões antigas só
mudam quando a placa as encerra. Testes host e compilação devem anteceder flash.

Segurança: verificar porta/chip/flash e as duas cópias do backup original,
verificar imagem ≤ partição factory e saída esptool; gravar apenas bootloader,
tabela e app, sem erase geral/NVS/efuse/GPIO. Recursos Docker têm nomes únicos
e limpeza própria; se houver colisão, parar sem tocar em recurso existente.
Relatório público apenas com contagens, duração, hashes de artefatos sem
segredos e estados PASS/FAIL. Falha real fica registrada sem marcar E02 aceite.

Limites: campanha curta não prova energia, produção, heap total, matriz TLS
exaustiva ou revogação automática de sessões ativas.

## rev2 — pré-preparo privado

O preflight do gerador E02 recusou os arquivos porque passou a pasta de
certificados sem resolver seu caminho canônico exigido por `private_file`.
Resolver o diretório privado antes de validar os arquivos e repetir o preparo.

## rev3 — sintaxe de caminho no OpenSSL Windows

O CRL privado ainda falhou ao gerar no preflight. Usar barras `/` nos caminhos
absolutos do arquivo de configuração do OpenSSL Windows e repetir sem imprimir
o conteúdo de chave ou diretório privado.

## rev4 — formatação do firmware

O cross-build passou, mas `cargo +esp fmt --check` pediu apenas formatação em
`build.rs`/`e02.rs`. Aplicar rustfmt e repetir build para garantir que o binário
gravado corresponde exatamente às fontes finais.

## rev5 — porta publicada do laboratório

O primeiro comando físico parou no preflight, antes de Docker/flash: o firmware
usa porta host 28883, publicada para 8883 no container. O harness presumiu
8883 também no host. Aceitar a porta privada existente na faixa não privilegiada
e conservar o mapeamento explícito para 8883; repetir os pré-requisitos.

## rev6 — diagnóstico sanitizado do preflight

A segunda tentativa parou antes de flash com limpeza concluída, mas o relatório
registrou apenas FAIL_PRECHECK. Adicionar códigos de etapa fixos ao relatório
privado para localizar a falha sem registrar paths, chaves ou saída do Docker.

## rev7 — readiness do container

O código de etapa localizou a falha em READY_BROKER, ainda antes de gravar a
placa. Registrar no relatório privado somente uma classe fixa do último erro
de startup, sem a linha de log, para distinguir CRL/TLS/arquivo/porta.

## rev8 — classe CRL ainda ambígua

O erro pertence à classe CRL, mas ela inclui validade, emissor e assinatura.
Refinar apenas a classificação sanitizada para orientar a correção do fixture;
nenhuma tentativa chegou ao flash.

## rev9 — detalhe redigido do erro CRL

A subclasse permaneceu ambígua. Guardar somente a última linha de erro no
relatório privado, redigindo qualquer caminho do mount TLS, para identificar
se o PEM está vazio ou se o verificador recusou seu conteúdo.

## rev10 — extensão AKI da CRL

O erro sanitizado foi `ClientVerifier(... CRL ... ParseError)`: o OpenSSL gerou
CRL sem Authority Key Identifier. Igualar o fixture P100 com
`authorityKeyIdentifier=keyid:always`, repetir o preflight e só então gravar.

## rev11 — limite do diretório temporário

Antes da limpeza recursiva automática do caso privado, verificar que o caminho
canônico criado é filho direto do diretório privado explicitamente indicado.
Isso preserva o escopo da campanha em Windows.

## rev12 — nome do relatório privado

Salvar futuras execuções sob prefixo `e02-result` para distingui-las dos
relatórios E01 anteriores no mesmo diretório privado. Conteúdo sanitizado e
regra de criação exclusiva permanecem iguais.
