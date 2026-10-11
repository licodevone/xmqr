# Aceite da fase 1 — quotas, limites e distribuição

Estado atual: **ACCEPTANCE_BLOCKED**. Os critérios são avaliados nas árvores atuais, sem usar instalação/estado do operador como laboratório. Não iniciar fase2 ou criar tag de aceite enquanto gates abaixo permanecerem pendentes.

| Critério | Evidência atual | Estado |
| --- | --- | --- |
| Quotas TOML/defaults e rejeição de configuração inválida | P55 implementado; testes portáveis anteriores registrados, negativos Unix existentes | Implementado; aceite Unix pendente |
| Redução de estado sem perda, v1/v2, Will saturada | tests/state_limits.rs, router/store e harness P55; execução Unix indisponível nesta conta | BLOCKED |
| Pacote completo65536 / N+1 e payload4096 / N+1 no broker | P58:12 testes codec, fmt, Clippy e build PASS Windows | PASS portátil |
| Limites/diagnósticos e conexão no client | C38:29 unitários+20 wire, fmt, Clippy/build PASS Windows | PASS portátil; integração real BLOCKED |
| QoS0/1/2, retained/fila/inflight, C37 e regressão TCP | Runner P59 usa builds próprios e harness P54/P55/Will/C27/C38 | Preparado; execução Unix BLOCKED |
| Interop independente Mosquitto | Runner confere clients/std buf e executa verify_interop se disponíveis | BLOCKED nesta sessão |
| Instalação/upgrade/rollback Ubuntu26 | Lifecycle old/new explícitos, hashes e preservação em container descartável | Preparado; execução real BLOCKED |
| Publicação de marco P52/P54/P55 e limites | Depende dos gates atuais e pacotes do commit aceito | Pendente; sem nova tag/release |

A suíte geral broker no Windows nesta retomada terminou exit101:41 PASS,25 FAIL de fsync Unix e1 ignorado. Isto não é PASS global nem comprova recuperação. O fsync permanece obrigatório. O client tem49 testes portáveis aprovados; estes fixtures não substituem integração com broker real.

## Contrato e compatibilidade

Broker P58 e saída SUBSCRIBE do client contam primeiro byte+Remaining Length+corpo no teto completo65536. Payload4096 e tópico1024 continuam preservados. Na recepção, rumqttc0.25.1 verifica apenas Remaining Length: C38 reserva header máximo5 e limita corpo65531. Isso mantém pacote recebido<=65536 inclusive encoding não mínimo; pode recusar por1byte um frame canônico de65536. Essa diferença defensiva está documentada e não afeta mensagens que o broker suporta com payload4096/tópico1024. Não anunciar fronteira inclusiva inbound idêntica à saída.

Formatos duráveis e quotas permanecem iguais; não truncar dados. A contagem corrigida do broker recusa frames que antes passavam apenas por não contabilizar o cabeçalho. Restaurar quotas suficientes é a recuperação prevista para estado incompatível; não editar WAL/snapshot.

## Execução no Ubuntu do operador

O Ubuntu26 informado pelo operador contém versões instaladas destes softwares. Isso não impede testes em portas livres loopback e diretórios temporários. Não desinstalar nem operar serviços/estado instalado para estes gates. A conta Windows de execução desta sessão é lico\codexsandboxoffline; tentativa wsl.exe --distribution Ubuntu-26.04 --exec uname -a retornou WSL_E_DISTRO_NOT_FOUND, embora a distribuição esteja aberta no login do operador.

No terminal Ubuntu, com os fontes finais já commitados e sem editá-los durante execução:

```sh
cd /mnt/d/projects/my-project/rapidez-projects/rapidez-broker-client
python3 -B xmqr/scripts/verify_phase1.py --client-root xmqr-client
```

O runner não usa sudo, APT, systemctl ou binários instalados. Usa targets separados, estado em /tmp, Cargo locked/offline e gera target/phase1-*/summary.json, logs e fingerprints antes/depois. Mudanças de fontes/HEAD durante execução invalidam resultados. Toolchain/cache/pre-requisitos ausentes são bloqueios a resolver no ambiente antes de repetir; nada é instalado automaticamente. Compartilhar o caminho de summary.json permite conferir os logs no workspace.

Mesmo UNIT_INTEGRATION_PASS não encerra a fase: o gate de pacote permanece separado. Consulte [aceite de pacote](phase1-package-acceptance.md) para Docker descartável, quatro artefatos antigos/candidatos, install/upgrade/rollback/remove/purge. Não executar packaging/test_package.sh no Ubuntu real do operador. Não usar arquivos privados de estado/credenciais nos anexos.

Após os gates, selecionar versões independentes e coerentes, validar manifests/notas/artefatos do commit exato e hashes, testar upgrade/rollback; somente então criar tags imutáveis e publicar experimental/pre-release autorizado. Tags existentes não serão movidas para conter este código.

## Registros

- [P55 — quotas e Will](../prompts/registros/P55-quotas-estado.md)
- [P58 — pacote completo](../prompts/registros/P58-pacote-completo.md)
- [C38 — limites do client](../../xmqr-client/prompts/registros/C38-limites-fase1.md)
- [P59 — pacote e runner](../prompts/registros/P59-aceite-pacotes.md)
- [P60 — coordenação](../prompts/registros/P60-fechamento-fase1.md)
