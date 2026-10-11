# P61 — fechamento da fase1

2026-10-11, Ubuntu26.04/WSL2 amd64, rustc1.99.0. Entrada broker49edfc2 e
client35580ba, árvores limpas. PromptsP61/P55rev4-5/P59rev2.5 e C38rev5/C39
precederam suas correções/versões. User autorizou tags e releases ao concluir.
Versões independentes: broker0.11.0/client0.7.0; tags anteriores imutáveis.

## Tentativas e correções

1. Runner target/phase1-20261011T230555Z-4gsyc_b7: INCOMPLETE. Broker88 testes
   internosPASS, mas teste de startup da fixture sem marcador de perfil falhou;
   Clippy do client recusou assert_is_empty; Mosquitto fora do PATH foiBLOCKED.
2. Marcador open-lab adicionado só na fixture; asserção do client compara len0
   sem imprimir saída. Runner target/phase1-20261011T231924Z-2fxnji6_: todos gates
   PASS exceto texto da recusaP55: runtime emiteDebug Limit("sessions"), teste
   esperavaDisplay. RevisãoP55rev5 aceita motivo específico emDebug/Display,
   preservando hashes, ausência de listener e reabertura. Sem afrouxar runtime.
3. Runner final target/phase1-20261011T232424Z-scjb4yeg: UNIT_INTEGRATION_PASS,
   todos gates e fingerprints antes/depoisPASS. Cache nativo /tmp existente
   evita novos targets volumosos; Cargo continua executando todos os gates.

Mosquitto2.0.22 e libs extraídos em /tmp, sem instalação. Tentativa inicial de
diretório com variável transferida falhou(cd null). Primeiro ensaio de sub
falhou por libcjson1 ausente; dependência temporária disponibilizada e4 testes
externosPASS. Primeiro lifecycle falhou por exclusão padrão de /usr/share/doc
da imagemDocker, embora pacote incluísse os arquivos. P59rev2.5 habilitou só
docsXMQR no container antes deAPT, mantendocmp. Lifecycle candidato e finalPASS.
Dois patches documentais recusados por cabeçalho/alvo repetido; revisões lidas
e aplicadas sem alteração runtime; tentativas não foram anunciadas comoPASS.

## Aceite real

- Broker:103 testesPASS, inclusive88 internos,4admin,4main,1backup,5config e
  1teste cobrindo12 imagensv1/v2 acima de quotas. Sem ignorados no Linux.
- Client:52 testesPASS,31unit e21wire. Fmt/Clippy -D warnings/build/inventário
  dos dois projetosPASS; fontes/manifests finais conferem com snapshot testado.
- Integração: P54TCP1, P55quotas7, Will9, C27(TLS/reconexão)4, C38fronteiras5
  e Mosquittoopen-lab4, todosPASS. Shutdown release:3PASS.
- Systemd real com units e estado temporários: start/pub/sub/reload/restart/stop
  mTLSPASS, incluindo shutdown durável e cancelamento do client.
- Pacotes otimizados Ubuntu26amd64: install0.10/0.5, upgrade0.11/0.7,
  rollback, remove e purge em container novoPASS; docs/arquivos/hashes/modos
  e preservação de dados fictícios verificados. ImagemUbuntu digest
  sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7.

Logs de pacote/systemd/shutdown em target/phase1-release-assets; logs unitários
e integrações no runner final acima. Logs ignorados noGit; este registro guarda
resultados/limitações. Runner mantém phase1_accepted=false porque não executa
pacote: aceite combinadoP61 agrega lifecycle separado, sem adulterar resumo bruto.

## Artefatos finais

| Artefato | SHA-256 |
| --- | --- |
| xmqr-broker_0.11.0-1_amd64.deb | 4b5017bf17ca5886c0aa359bab47135ba72e9c29754af800a9990d4f0364b6d6 |
| xmqr-client_0.7.0-1_amd64.deb | fb216ddb47ad24d2870e3f7a8e8c5f0b55b47e946e14148d53394b8f74ecdc92 |

GuiaTOML final reconstruído no pacote e lifecycle repetido antes da publicação.
Manifests/fontes testados preservados; ajustes finais após runner são docs.
Publicação autorizada: tagsv0.11.0/v0.7.0 e prereleases nos dois repositórios,
com deb, checksum e resumo de aceite. Não declarar CI remotaPASS sem consulta.

## Limites e próxima fase

PHASE1_ACCEPTED no escopo Ubuntu26/WSLamd64. Sem alteração/upgrade/desinstalação
dos serviços, credenciais ou estado reais do operador. TOML opt-in; defaults e
estado preservados. Inboundclient conserva cap65531/body e possível recusa de
frame canônico65536 por1byte. Ubuntu24, arm64, Windowsbroker e MSRV1.88 exato
não homologados. Mosquitto externoopen-lab; TLS/ACL externo não reivindicado.
Releases experimentais, sem repositórioAPT próprio ou prontidão produção/MQTT5.
Próxima fase: capacidade/RAM/CPU/latência e fan-out, prompt próprio; não iniciada.
