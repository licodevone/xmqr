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
