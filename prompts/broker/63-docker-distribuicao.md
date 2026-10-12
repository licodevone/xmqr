# P63 rev1 — distribuição Docker broker/client

Entrada brokeraa5fda4 (runtime0.11.0), client890829f (0.7.0), árvores limpas.
Pedido: evoluir ambos e criar versãoDocker; cada release terá debUbuntu.
Escopo: Dockerfiles com labelsOCI/stop signal, harness mTLS entre containers,
docs atualizados, versões patchbroker0.11.1/client0.7.1 e registros/P63/C40.
Sem novos protocolos/quotas/registro de imagens externo não solicitado.
Aceite: builds linux/amd64 dos dois, usuário10001, volumes/segredos externos,
CA/SAN corretos, pub/sub QoS e retained/restart, shutdown durável, negativos de
CA/credencial; rootfsread-only/caps removidas e cleanup dos recursos de teste.
Artefatos: docker save gzip comSHA, debUbuntu26 testados install/upgrade/rollback,
tags imutáveis e prerelease nos dois repos. Prompts antes de qualquer edição;
falhas exigem revisão antes de correção. Não operar serviços/dados do operador.

## rev2 — ambiente e proveniência

BuildsPASS; DockerCLI WSL indisponível e docker.exe não executável por interop.
Rodar harnessWindows com OpenSSL doGit instalado, hashfixture público gerado
noWSL e transportado porarquivo, sem segredo real. Acrescentar args explícitos
--openssl/--hash-file, mantendo CLIdefaultDocker. Não modificarDockerDesktop.
Imagens iniciais só validação; após commit das fontes, reconstruir com revision
exata e repetir teste antes de exportar/publicar; não atribuir patch aHEADantigo.

## rev3 — coleta de logs do teste

Primeiro teste aguardava readiness só emstderr e expirou; tracing padrão do
broker escreve emstdout. Combinar os dois streams apenas para asserts de logs,
mantendo saídaJSON do client separada. Não mudar logging/proteções do runtime.

## rev4 — contrato de payloadJSON e restart

Segundo ensaio conectou mTLS, mas assert procurava texto literal onde JSON
representa payload_bytes. Decodificar JSON e comparar bytes/topic/QoS/retain;
não alterar saída do client. Aguardar novo anúncio de listener após restart,
não apenas estadoRunning. Repetir teste completo e negativos.

## rev5 — diagnóstico da execução após restart

Ensaio chegou ao restart, mas client retornouexit1 e a exceção omitiu stderr.
Capturar diagnóstico estático do client em falha, sem stdout/payload. Investigar
antes de qualquer correção runtime; repetir com relatório novo após resolver.

## rev6 — filtro autorizado na fixture

Diagnóstico mostrouSUBACK recusado corretamente: bundle autoriza sensor/#,
mas teste de restart pediu sensor/value. ACL de assinatura deste perfil exige
filtro autorizado explícito. Reusar sensor/# no replay e conferir tópico exato
da mensagem; não ampliar ACL nem alterar broker/client.
