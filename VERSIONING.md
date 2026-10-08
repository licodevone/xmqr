# Versionamento

Tag v0.5.0 local/remota verificada em 2026-10-07, commit59c9e70. O titulo do
commit nao comprovava Last Will: o codec dessa base ainda recusava Will.

Metadados locais agora identificam 0.6.0 em Cargo.toml/Cargo.lock para o marco
retained/Last Will. Nao existe tag/release 0.6 criada por esta tarefa. O mantenedor
faz commit/push/tag somente apos gates e revisao do marco. Avise a prontidao e
aguarde essa publicacao antes de implementar/incrementar a proxima versao.

Ver [sequencia incremental](docs/incremental-versions.md). Minor 0.x.0 adiciona
fatias; patches 0.x.1, 0.x.2 etc corrigem defeitos. 0.6.54 representa 54 patches,
nao incremento automatico para feature. Nao ha promessa de conformidade integral,
estabilidade de API ou producao em 0.x. MIT preservada; MQTT5 fora deste trabalho.

## P43 - estado atual

Base HEAD bc4cc55 e tag v0.6.0 local/remota confirmados antes de P43.
Metadados locais agora 0.7.0 para monitoramento opcional, ainda em validação.
As referências acima à espera de publicação 0.6 descrevem a execução anterior.
Não criar release/tag 0.7 antes dos gates completos. Não avançar para 0.8.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integrações
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. Publicação0.7 fica com
usuário; sem commit/push/tag aqui. P44 segurança dinâmica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produção.
