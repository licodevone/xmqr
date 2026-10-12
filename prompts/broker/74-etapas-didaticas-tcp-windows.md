# P74 rev1 — snapshots cumulativos P03/P04/P05 para Windows

Entrada: P73 criou a base didática e passou gates nativos WindowsRust1.98.1.
Novo pedido autoriza fracionar em etapas cumulativas com código por prompt.
Executar aqui as próximas duas menores fatias: P04servidorTCP eP05clientTCP.
Não implementar todas as funcionalidades MQTT nem alterar broker/client reais.

Congelar P03 emcurso/projeto-inicial. Copiar base íntegra para curso/etapas/P04;
manter clientP03 e acrescentar broker deecoTCP loopback127.0.0.1:18830, buffer512,
atendimento sequencial epropagação Result/?. EmP05, copiarP04 íntegro e
acrescentar clientTCP: conectar, enviar4bytes ping, receber exatamente4bytes e
mostrar Resposta:ping. Preservar mensagens iniciaisP03; comentários identificam
P03 mantido/P04 acrescentado/P05 acrescentado. Versionamento didático separado.

Criar os promptsP04/P05 antes dos códigos. Registros/README por snapshot,
explicação de cada novo token/API/biblioteca padrão ecomando antes do uso.
README anterior permanece emhistorico; README atual não descreve comportamento
antigo como atual. Acrescentar roteiro das fases futuras, sem executar futuros
prompts/recursos automaticamente. Exportar ZIP próprio, diff contra snapshot
anterior, guiaHTML, checksums/manifestos com série claramente didática nova.
Linkar índice da nova série no índice histórico sem sobrescrever arquivos.

Validação nativeWindows: lockoffline/fmt/test/clippy/build/run; integração real
P04 ecofragmentado eP05 client contra broker. Extração ZIPsegura +build/run dos
projetos extraídos, sem target ouartefatosprivados. CARGO_TARGET_DIR temporário
por execução; não instalar nem mudar toolchainglobal. Porta só loopback em
processo temporário de teste e parar somente esse PID. Não alegar MQTT já pronto.
Revisar prompt antes de corrigir erro. Commit/push autorizados; sem release/tag
do broker/client distribuídos. Anexos preexistentes eP68 preparados preservados.

## Rev2 — comentários de comandos, funções e origem

Usuário exige explicação dentro do código e identificação das alterações
quando arquivo existente reaparece. Usar [Pxx - NOVO], [Pxx - ALTERADO] e
[Pxx - MANTIDO] junto dos trechos. Comentar imports, funções, I/O, parâmetros,
retornos e símbolos novos sem alterar comportamento. Consolidar comentários
da baseP03 ainda não publicada antes de congelá-la, manter clientP04 idêntico
à baseP03 revisada e destacar assinatura/manifest alteradosP04. P05 mantém
brokerP04 íntegro e comenta novas instruções client. READMEs/diffs registram
mudanças, incluindo comentários. Não modificar snapshot anterior após exportar.

## Rev3 — igualdade do conteúdo mantido

Revisão encontrou comentário posterior emmanifestP04 não copiado ainda para
brokerP05. Sincronizar somente esse arquivo mantido na cópiaP05 evalidar
igualdade byteabyte de todo brokerP04/P05 eclientP03/P04. Ajustar rótulo de
quatro linhas noGUIA inicial, pois os comentários ampliaram a listagem.
Regenerar artefatos eexecutar validação dos ZIPs finais antes de congelar.

## Rev4 — fechamento documental

Patch do registro final foi recusado por contexto textual divergente e não
alterou arquivos. Acrescentar evidência de UI/CRC usando contexto real do final
do registro. Não é falha dos programas; gates nativos e integração seguemPASS.
