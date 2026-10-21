# P242 - Client e admin nativos Windows: integracao e distribuicao

Versao 1.3 - 2026-10-21. Usuario autorizou continuar client/admin, agentes em
paralelo e escolha de modelos conforme complexidade. Frentes independentes:
C151 em xmqr-client, A27 em xmqr-admin; este prompt cobre integracao/packaging.

Revisao 1.1: OpenSSL do Git depende de objetos MSYS recusados pelo sandbox;
gerar certificados de teste com .NET CertificateRequest, sem instalar em store.
Python local nao possui Argon2; usar helper Rust independente de teste com senha
em stdin e perfil exato do broker, nunca para provisionar usuarios reais.
Cache compartilhado em Temp perdeu manifests/archives; restaurar caches privados
por componente, conferindo checksums dos archives e atualizando timestamps.
Nao atribuir causa externa sem evidencia nem remover caches em uso.

Revisao 1.2: fixture TLS deve incluir SKI/AKI exigidos pela verificacao estrita;
nao desligar verificacao de certificado. Wrapper de ACL requer tipo FILE
explicito em GetSecurityInfo; UNKNOWN_OBJECT retorna erro87 e foi corrigido
antes do aceite. Incluir teste integrado do sub continuo/parada CtrlBreak,
pub pela mesma configuracao e limite de saida sem truncamento/ACK antecipado.

Revisao 1.3: arquivo criado pelo operador precisa de normalizacao de owner/DACL
antes de LocalService. Entregar helper elevado limitado ao ProgramData registrado
do componente; recusar reparse/aliases e nao ler conteudo nem alterar arvore
arbitraria. Preparar runner SCM somente para VM descartavel, sem executar host.
Para windows-permissions0.2.4, que declara MIT mas omite arquivo LICENSE, incluir
texto canonico MIT de permissao/disclaimer com hash e manifests originais de
atribuicao, identificando explicitamente a omissao upstream. Nao inventar ano,
copyright ou substituir pelo notice de outro autor; fallback restrito a versao,
licenca e hashes. Validar interop contra hashes exatos incorporados no pacote.

Entrada: P241 broker com persistencia e MQTT Windows validados; client C150
recusa senha privada e sub em servico; admin A26 recusa token privado Windows.
Preservar alteracoes anteriores, AGENTS.md e docs/chat/P240 do operador.

Objetivo: client pub/sub autenticado em Windows, sub sem console com destino
privado e limite; admin HTTP loopback autenticado com token privado e banco de
usuarios protegidos; MSIs individuais e bundle com broker/manager atualizados.

Requisitos: ACL nativa fail-closed para arquivos/parentes, nunca remover a
protecao por conveniencia. Sem segredo em argumentos/config/log, sem relaxar
SAN/TLS. ACK de QoS1/2 somente apos escrita/flush suportado pelo modo de saida;
explicitar duplicacao/QoS2 e ausencia de garantia de entrega exatamente uma vez.
Permitir console com a mesma configuracao do servico para teste reproduzivel.
Dar LocalService acesso so aos dados privados necessarios; cfg raiz read-only.
Nao alterar pin Git do core nem formatos. Bridge/outbox e controle administrativo
Unix que nao tenham backend nativo continuam recusados explicitamente.

Aceite: testes reais ACL positivas/negativas, builds/markers nativos, client
com broker em TLS/mTLS, sub gravando arquivo privado, rejeicao de senha/SAN/CA
invalidas, painel admin com 401 sem credencial e status autenticado, encerramento
cooperativo. MSIs com licencas e checksums, testes WiX e bundle para download.
Instalacao/SCM/boot/ACL efetiva da conta servico ficam para VM descartavel elevada;
nao instalar no host nem declarar esses gates aprovados sem executar.

Validacao: suites locais e fmt/Clippy pertinentes, runner de interoperabilidade
Windows com estado proprio, markers, empacotamento seletivo e notices reais.
Registrar resultados/falhas/limites em prompts/registros/P242-windows-client-admin-runtime.md.
Sem commit, push, publicacao ou mudanca de versao nesta implementacao.
