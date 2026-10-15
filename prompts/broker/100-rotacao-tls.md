# P100 rev1 — B11: rotação transacional de certificado, CA e CRL

2026-10-15. Entrada `1e72082f5163ecba58b0ffa8aaf231df80ed41c3`,
broker0.13.1/release publicada; árvore limpa. P97/B10 e P98/B12 aceitos.
Pedido do mantenedor: finalizar fase4 e ensaio físico E02 na COM4.

Objetivo: em `secure-mtls` e `tls-password`, SIGUSR1 local solicita recarga
dos mesmos caminhos TLS de startup. Validar o candidato completo (certificado,
chave correspondente, período de validade do certificado/CA, CA/CRL e política
TLS) fora das tarefas de conexão; publicar uma única geração para **novos**
handshakes. Falha mantém a geração antiga. `secure-mtls` conserva certificado
cliente obrigatório; `tls-password` conserva autenticação e ACL obrigatórias.

Escopo: transporte, watcher/sinal em main, validação TLS, testes e campanha
externa, documentação e registro. Não recarregar TOML geral, usuários/ACL ou
estado, não mudar wire MQTT/quotas nem desconectar sessões já aceitas.
SIGHUP permanece exclusivo do bundle dinâmico. Rotação CA/CRL só afeta
handshakes posteriores; sessões existentes precisam de encerramento controlado
para revogação imediata. Não registrar PEM, chaves ou caminhos privados.

Aceite: troca cert/key válida, CA/CRL e reversão; erro de chave, PEM, CA vencida,
CRL inválida/vencida mantém endpoint anterior; dois endpoints mTLS observam a
mesma geração; conexões existentes continuam sob sessão TLS antiga. Testes
negativos e integração com client C48, regressões mTLS/B10 e gates Rust/Ubuntu26.
E02 físico usa somente após esse aceite. Versão/tag/release em marco próprio
após evidência; não inferir aprovação por código compilado.

## rev2 — lint do watcher

O primeiro Clippy recusou `match` com um único padrão de sucesso no watcher.
Trocar por `if let` com ramo de erro genérico, sem alterar o contrato de
publicação/rollback; repetir o gate.

## rev3 — diagnóstico de startup do harness

O primeiro ensaio externo falhou antes do listener, sem evidência da causa
porque o diretório temporário foi removido. Expor somente a última linha
diagnóstica do broker com caminhos temporários mascarados quando o startup
falhar; manter credenciais e PEM fora da saída. Corrigir a fixture segundo o
erro real e repetir a campanha.

## rev4 — CRL de fixture

O broker rejeitou o CRL OpenSSL inicial com `ClientVerifier(ParseError)`.
Gerar CRL v2 com extensão authorityKeyIdentifier, mantendo CA e serial do
laboratório; verificar que o CRL é aceito por rustls antes de avaliar a rotação.

## rev5 — vínculo criptográfico do CRL

Antes de publicar uma geração, validar que cada CRL corresponde ao sujeito de
uma CA configurada e que sua assinatura verifica com a chave pública dessa CA.
Recusar combinação CA/CRL divergente, além da validade temporal. Adicionar
negativo externo de CRL de outra CA e repetir o gate.

## rev6 — lockfile da verificação de assinatura

O gate `--locked` recusou a ativação nova de `verify-aws` porque Cargo.lock
ainda refletia a variante sem essa feature. Atualizar o lock com Cargo
compatível com MSRV1.88 e repetir Clippy/build bloqueados; não tratar como
falha funcional da rotação.

## rev7 — negativos de validade e assinatura do CRL

Ampliar o harness com CRL vencido e CRL de assinatura alterada, além do CRL
de outra CA. Cada SIGUSR1 inválido deve conservar clientes novos na geração
anterior. Repetir a rotação e a reversão válidas após esses negativos.

## rev8 — modo TLS com senha

Estender o harness P97 para provar que `tls-password` usa o mesmo mecanismo
SIGUSR1: chave inválida mantém o certificado anterior, cert/key novo muda a
confiança do client e rollback restaura o anterior, sem exigir cert do client.

## rev9 — sincronização do ensaio externo

As verificações negativas com espera fixa poderiam passar antes do watcher
processar o sinal. Sincronizar cada afirmação ao registro genérico de geração
aceita/recusada (sem PEM/segredo) dentro do laboratório, com prazo finito;
repetir as campanhas. Não inferir rollback por ausência de evento observado.

## rev10 — validade do certificado do servidor

Ampliar negativos externos com certificado do servidor expirado e PEM
malformado antes do swap válido, exigindo recusa observada e geração anterior
conectável. Repetir a campanha após a ampliação.
