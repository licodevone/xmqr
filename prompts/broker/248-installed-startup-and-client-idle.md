# P248 - Confirmacao de inicio e Client persistente

Versao1.5, 21/10/2026 America/Sao_Paulo. Base0fbe2dec preservada.

FlagASDATAFILE2 passou auditoria10recursos/5secoes CodeIntegritytrue, porem
CreateProcess da copia modificada retornou AccessDenied e depois a copia
deixou de existir (inclui copia diagnostica). Raw compilado continua presente.
Consulta Defender/Operational negada; NAO afirmar antivirus/quarentena como
causa comprovada, nao desabilitar protecoes/ACL nem repetir copia recusada.
Apresentado antes do proximo ajuste: incorporar ICO Client no link nativo
do manifesto windows-service por recurso SDK (.rc/.res), mantendo codigo
C152 e identidade visual. Novo build valida icone por leitura apenas e prova
capabilities/version; sem alterar binario depois de compilado. Artefato so
apos verificacoesPASS. Escopo inclui build.rs/asset no manifestoClient e
verificador de icone readonly; nao executar MSIs/SCM nem alterar protecoes.
Build-windows passa a validar/copiar o Client ja marcado no link, sem nova
mutacao de recursos. Demais componentes mantem fluxo existente, com prova
--version depois do empacotamento de recursos para recusar copia nao executavel.

Retentativa5s nao resolveu32. Prova somente leitura: arquivos existentes
bruto/P246 carregam flags2/34 semerro; erro ocorre so na copia recem-atualizada.
Diagnosticar em copia descartavel do helper flagsAS_DATAFILE2 (sem image-map)
ou copia de verificacao byte-identica, mantendo Find/LoadResource byte audits,
nao executando o PE nem enfraquecendo as checagens de secoes/codigo/entrada.
Mudanca permanente somente se prova concreta passar; fonte executavel intacta.

Diagnostico concreto do segundo staging: NativeError32 (sharing violation),
nao accessdenied. Mesmo helper/pastaTemp falharam no LoadLibraryEx apos
EndUpdateResource. Antes do ajuste, apresentar escopo ao usuario: retentativa
limitada a ate5s SOMENTE Win32 sharing/lock violations32/33 nessa leitura de
recursos. Nao relaxar integridadePE, nao executar DllMain, nao remover arquivo
alheio, nao ampliar ACL. Testar PE real, nove imagens/dezrecursos e sourcehash.

Primeira aplicacao de icone em copia nova compilada falhou em verificacao
LoadLibraryEx resource-only; helper removeu somente propria copia incompleta.
Nao enfraquecer auditoriaPE nem usar executavelantigo. Diagnosticar codigo
nativo, repetir staging em pasta temporaria nova (como fixturesC152), com
mesmo helper e integridade. Sem alterar binario fonte ou instalacao real.

Revisao solicitada pelo usuario: retomar apresentacao no chat ANTES das
proximas correcoes, como P47/C31 Ubuntu (ambos lidos). Os prompts Windows
anteriores existiam em disco mas nao foram apresentados antes de executar.
Esta revisao organiza escopo/aceite/resultado no mesmo contrato, sem executar
features futuras nem converter autorizacoes historicas Ubuntu em releaseWindows.

## Estado de entrada e objetivo observavel

Client independente base44e13a4b/0.43.0; arvore inicialmente limpa para C152.
Broker base0fbe2dec com P244-P247 locais preservados. Objetivo: servico Client
continua ativo quando nao ha mensagens por mais de90s; CLI normal conserva
politica anterior. Broker/Admin ja responderam viaHTTP, configuracao pronta.

## Migracao Ubuntu para Windows nesta fatia

Unit systemd -> adaptador SCM; SIGTERM/SIGINT -> Stop/Shutdown cooperativos;
0600/donoUID -> owner/DACL privados; deb -> binarioWindows com hash e updater
restrito nesta correcao. MSI, tray, boot/logon e upgrade completos sao gates
separados, nao aceitos apenas porque compilou ou atingiu Running uma vez.

## Escopo, compatibilidade e invariantes

Somente Client no fluxo C152 MQTT3.1.1 e atualizador do exe; sem alterar wire,
estadoMQTT, quotas, TLS/SAN/ACL, usuario/senha/certificados, Broker/Admin,
configuracoes ou versoes. Preservar prazos de protocolo/total, reconexoes
limitadas, QoS2, outputduravel8MiB e parada cooperativa. Sem reinstalar.
Arquivos: prompt/registro/docsP248, scripts/update_windows_client_p248.ps1,
artefatospublicos; C152 possui fontes/testes/manifestsdev/registro do Client.

## Validacao e aceite da entrega

fmt/test/clippy/build nativo locked; servico espera alem90s, CLI expira,
protocolo continua limitado e Stop/totalcancelam. Registros de falhas/revisoes
antes de corrigi-las. Updater parseado e helpers provados com temporarios,
backup e hash/registro/caminho exatos; icone com codigoPE preservado.
Somente apos gatesPASS preparar pacote com exe atual/manifesto/checksums.
Operador observa100s o Client instalado e confirma; se bloqueado, informar
causa concreta/acao possivel, nunca simular resultado ou empacotar binarioantigo.
Sem commit/push/tag/releaseMSI automaticos. Proximas fatias exigem promptproprio.

## Evidencias e limites atuais

P247 reportCreatedUtc2026-10-22T02:04:52Z FilesPrepared/StartupSucceeded true,
tres Running; captura image(20261022-020528).png confirma. Broker health200,
ready200 e Admin authconfig200 setup_required true. Client conecta uma vez,
mas metricas agora active0/session1/authreject0. Leitura confirma deadline
de aplicacao90s que nao renova em PINGRESP; fatia C152 corrige servico3.1.1.

Escopo: acompanhar C152, testar/read-only health e coletar metadados permitidos;
preparar atualizador restrito do exe Client SOMENTE se novo build for validado.
Atualizador operadoradmin, parar Client, hash/caminho exatos, backup exclusivo,
copiar novoexe validado preservando configuracoes/credenciais, iniciar/checar,
rollbackbinario se substituir falhar. Nao executar hostupdate automaticamente.
Nao rerodar inicializador P247 nem novos MSIs/versoes.

Aceite: manter estado/seguranca; exe com capabilities/icone Client corretos,
revisao e testes de temporarios, nenhuma credencial no artefato/log. Se falta
build, nao entregar exe antigo como corrigido. SCM/reconexao/estabilidade reais
pendentes do operador quando token das ferramentas nao elevado. Registrar
resultados reais e atualizar chat sem alegar tres servicos sustentados apenas
pelo snapshot Running inicial. Sem commit/push/tag.

## Revisao1.6 - manifesto publico de licenca

Conferencia de entrega recusou suffix.toml em notices/licenses/windows-permissions
(Cargo.toml publico incluido nos avisos do fornecedor), nao arquivo instalado.
Antes de corrigir: permitir manifests publicos somente sob notices/; continuar
recusando extensoes de chaves/certificados em qualquer lugar e TOML runtime
fora de notices. Allowlist de caminhos e checksums de todos os arquivos mantida.
Nenhuma mudanca de codigo/runtime nem reducao da protecao de credenciais.
