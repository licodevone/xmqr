# P227E v1.0 — relógio lógico e expiração durável sem renovar TTL

Preparado em18 de outubro de2026 antes de testes/fontes desta correção.
Complementa P227, sem reabrir as correções aceitas P227C/P227D. Base de leitura:
broker0.42.0, documento v15; conferir HEAD e dirty antes de cada commit.
Coordenação autoriza clock/router/store/mod.rs e testes próprios. Codec é de
outra frente, Cargo/versão/admin/release pertencem ao coordenador.

## Lacuna original, não extensão nova

[P130 rev1](130-message-expiry-mqtt5.md) exige: persistir instante absoluto e
intervalo original para o cálculo encaminhado. StoredMessage atualmente só
guarda expiry_at_unix_ms; remaining_message_expiry subtrai SystemTime::now.
Recuo UTC após recebimento pode aumentar TTL, inclusive acima do original.
O teste existente cobre pré-epoch/overflow, não regressão com tempo live.

[OASIS MQTT5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
§3.3.2.3.3/MQTT-3.3.2-5/-6 requer descartar cópia cujo encaminhamento ainda
não começou e reduzir o intervalo encaminhado pelo tempo aguardado. Não
transformar isso em promessa de NTP/energia ou deadline físico exato. O
comentário não normativo §3.1.2.11.2 admite relógio parado durante downtime;
não autoriza aumentar TTL durante o processo. Somente limitar ao intervalo
original é insuficiente depois de parte do tempo live já ter decorrido.

## Desenho mínimo e compatibilidade

1. Relógio de expiração único, compartilhado pelo router e handler, com
   Instant para progresso do processo e piso UTC lógico que nunca recua.
   Salto UTC adiante pode avançar esse piso; recuo não o reduz. Amostragem
   barata com atômicos, sem locks bloqueantes/disco no cálculo. Pré-epoch,
   overflow e entrada monotônica inválida falham fechado. Fonte sintética
   de teste por instância, sem flags públicas nem mudança do relógio host.
2. Guardar watermark lógico no agregado e intervalo original opcional em
   StoredMessage. Toda transição candidata usa o mesmo relógio e grava o
   watermark antes da barreira WAL. Calcular deadline com esse relógio;
   preservar intervalo original em retained/offline/QoS e na publicação do
   Will, sem alterar handshake já iniciado ou ownership QoS1/2.
3. Documento v16: os novos campos em tipos deny_unknown_fields não podem
   ser disfarçados de v15 compatível. Ler v1–v15, escrever v16; recusar
   futuro/corrupção/quotas sem truncamento. Legacy sem intervalo original
   permanece None: não inventar histórico. Na primeira recuperação legada,
   usar UTC disponível; proteção de watermark começa com o primeiro commit
   v16. Não reconstruir tempo/perda anterior à migração. Restore v16 parte
   do máximo entre UTC e watermark e volta a progredir por Instant.
4. Admin independente precisa novo pin/core e prova v16 antes de publicar;
   coordenador fará isso após checkpoint funcional validado. Rollback a
   broker/admin v15 exige backup privado anterior, não converter estado
   ativo. Sem edição de Cargo/admin nesta fatia.

## Fronteira de commit, encode e início do encaminhamento

Para uma cópia com expiry cujo encaminhamento ainda não começou, pedir ao
ator uma permissão de envio: instante lógico T, deadline e R segundos inteiros
restantes (arredondamento para cima), limitado ao original quando conhecido.
O ator persiste watermark>=T antes de liberar essa permissão. Falha WAL não
autoriza encode/envio nem se mascara como mensagem expirada.

Depois da barreira, imediatamente antes de encode/iniciar write, conferir o
mesmo relógio. Só emitir o R certificado enquanto o restante pertence à mesma
faixa inteira R. Se caiu, obter permissão nova com watermark novo; se venceu,
não iniciar o envio e concluir descarte durável pelo caminho existente. Não
emitir TTL menor não coberto por checkpoint: após restore o watermark dessa
faixa garante TTL<=último R emitido, mesmo com UTC recuado. Não reservar
watermark futuro nem encurtar artificialmente validade para esconder a janela.

Refresh é limitado por deadline monotônico explícito de3s e no máximo4
tentativas, sem loop ilimitado se cada fsync consumir uma faixa. Esgotamento
encerra/retorna erro preservando obrigação durável; erro de persistência
propaga falha, não ACK/sucesso. Encode e início do write não têm awaits entre
a checagem final e a chamada de escrita. O instante considerado é o início
do encaminhamento pelo software, não a confirmação física do primeiro byte.
Após iniciado o handshake/envio, não cancelar QoS por expiração posterior.
Quotas, canais e deadlines existentes permanecem, sem nova fila ilimitada.

## RED → GREEN e aceite

Commitar este prompt antes das fontes. Preparar RED determinístico para
relógio live recuado e tempo decorrido, retomada com watermark e TTL já
encaminhado. Não ajustar relógio global/WSL, instalar ou tocar serviços.
Revisar prompt após qualquer falha inesperada antes de corrigir fonte.

Testes: intervalo10, avanço3s→7, recuoUTC com avanço monotônico→6 e depois
expira; salto adiante não ressuscita em recuo; pré-epoch/overflow; original0
e U32_MAX. Live/retained/offline e recuperação v16 não aumentam prazo. Tempo
avança durante commit falso: mesma faixa libera, cruzamento exige checkpoint
novo, limite falha sem entregar/perder ownership. WAL injetado recusa envio.
Migração sintética v1–v15 preserva dados e marca honestamente sua origem;
fixture real v15→v16 será coordenada com binários congelados. Legado sem
original permanece ausente. Testar novo formato, recusa por antigos e pin
admin antes da distribuição, não declarar isso só por existir parser.

Executar fmt dos arquivos próprios e testes dirigidos locked/-j1 em janela
Cargo coordenada; regressões de expiry/session/Will/QoS/flow/migração.
Principal faz gates completos, wire e distribuição após congelar fonte/ELF.
Não alterar codec, CI, Cargo/versão, bridge/C129 alheios, hardware/firewall,
tags/push/release nesta implementação. MIT/terceiros preservados; registrar
PASS/FAIL/BLOCKED e limitações sem promover evidência histórica.
