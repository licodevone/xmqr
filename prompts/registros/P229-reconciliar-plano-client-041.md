# P229 — plano e versões após client 0.41.0

Prompt [P229 v1.0](../broker/229-reconciliar-plano-client-041.md) foi
publicado antes da alteração documental. Fonte do client
`1d60d382782ec33ed876b8b43d1c87503df7ef86`,
[CI final](https://github.com/licodevone/xmqr-client/actions/runs/39170753201)
cinco jobs PASS e [prerelease v0.41.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.41.0)
com seis anexos remotos conferidos. Pacote `.deb` da CI SHA-256
`ca68df0788d62ec2d63701eea07e63a168f4cdc26b0bbd10142dc163f686e6a7`.

`docs/evolution-plan.md` registra C137/C138 como fatia aceita e mantém
fase 8 desmarcada. `docs/current-releases-wsl.md` aponta para broker
0.43.0, client 0.41.0 e admin 0.11.0 com hash e comando corretos;
rollback do client só é seguro com instâncias MQTT 5 paradas e opção nova
removida. `docs/plano-paridade-mosquitto.md` atualiza T02 e explicita
que as linhas históricas M01–M10 não substituem o aceite vigente da fase 6.

Validação documental: `git diff --check` PASS; links e três hashes foram
conferidos com registros/releases; sem mudança funcional ou claims de
fase 8 concluída. Windows nativo e distribuição estendida permanecem
abertos.
