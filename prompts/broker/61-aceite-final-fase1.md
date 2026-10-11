# P61 rev1 — aceite final da fase1 no Ubuntu acessível

Base broker49edfc2/client35580ba, árvores limpas. Pedido: finalizar fase1.
Ubuntu26/WSL agora listado no login lico/licod; confirmar ferramentas reais.
Executar runnerP59 congelando árvores; gates atuais, interopMosquitto e pacotes
em containerUbuntu descartável, sem alterar instalação/estado do operador.
Após aceite de código, selecionar versões candidatas independentes, atualizar
manifests/changelog e preparar pacotes do commit exato; repetir checks afetados.
Escopo: evidênciasP61, aceite/roadmap/versionamento e release validada. Corrigir
falhas apenas após revisão do prompt responsável. Preservar fsync,TLS,quotas.
Commit/push e tags/releases autorizados; tags existentes imutáveis. Sem fase2.
Aceite final exige UNIT_INTEGRATION_PASS, interop externa, PACKAGE_LIFECYCLE_PASS,
hashes/artefatos e documentação coerente. Bloqueios não serão chamados dePASS.

## rev2 — resultados iniciais e correções necessárias

Runner inicial terminouINCOMPLETE: fixtureP55 sem marcador de perfil; Clippy1.99
recusou assert!(stdout.is_empty()) no client; Mosquitto ausente do PATH capturado.
RevisarP55/C38 antes das correções. FerramentasMosquitto extraídas em /tmp,
incluindo libcjson1 cuja falta causou dois timeouts no ensaio externo; após
disponibilizar a dependência,4 testes externosPASS. Uma tentativa de preparar
diretório por variável transferida ao bash falhou (cd null); usar caminho de
teste explícito. Não alterar proteção do perfil ou exposição de saída do client.

Runner levará builds a /tmp nativo (logs/fingerprints continuam no workspace),
evitando custo de metadata no driveWindows. Não reutilizar binários instalados.
Selecionar broker0.11.0/client0.7.0; criar promptC39 antes dos arquivos do client.
Repetir gates nas árvores congeladas, comPATH/LD_LIBRARY_PATH temporários de
Mosquitto. Aceite de pacote continua separado. Nenhuma fase2 nesta tarefa.

## rev3 — gates adicionais e cache nativo

Segundo runner: todos gatesPASS exceto representação de erro do testeP55,
registrada emP55rev5. Corrigir sem afrouxar motivo. Permitir --build-cache-root
apenas para pasta nativa existente /tmp/xmqr-phase1-build-*; Cargo ainda executa
todos os checks, sem pular build/test. Reusar cache evita exceder /tmp ao repetir.
Primeiro lifecycle falhou pois imagemUbuntu descarta /usr/share/doc por padrão:
habilitar só docsXMQR no container, registrado antes emP59. Mantémcmp obrigatório.
Primeiro patch da revisão falhou por cabeçalhoP59 divergente; nenhum fonte mudou;
ler cabeçalho real e aplicar revisão documental antes das correções.

## rev4 — registro documental final

Todos gates de código/interop e lifecycle candidatoPASS. Atualizar aceite,
README/changelog e registros, reconstruir pacote com guiaTOML final e repetir
lifecycle antes de tag. Uma substituição documental por delete/add no mesmo
patch foi recusada; usar gravação única UTF-8, sem modificar fontes de runtime.
