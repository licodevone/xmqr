# P92 v1.2 — gates finais e distribuição fase3

Preparado 2026-10-13 antes de versões/embalagem. P89 exige B06+B07+B08+C07
com evidência real. Broker patch0.11.6: recusas CONNECT corrigidas por P93,
sem formato/quota/dependência runtime nova. Client minor0.9.0: prazo total
opcional, jitter/cancelamento/prazos C45. Admin independente0.1.0 permanece
com pin e release anteriores se compatibilidade do formato for comprovada.
Não iniciar fase4. Alterações concorrentes pertencem aos agentes informados.

Gates nativos locked: fmt, teste completo, clippy-Dwarnings, release bins,
inventário MIT e avisos; falha requer revisão do prompt antes de correção.
P90 mutações reais com orçamento/seeds/watchdog; P91 3x600s reais de campanha
final TCP+mTLS, invariantes/recuperação/memória, Mosquitto2.0.22 independente
com matriz normativa e C45 ambos sentidos. Reexecutar B06 no código final.
Admin0.1.0 só compatibilidade, sem alterar pin/versão automaticamente.

Embalagem deve preservar os textos originais LICENSE/NOTICE, não apenas
inventário SPDX. Reutilizar coletor e suplemento valuable revisados A03 do
admin, verificar byte/SHA e metadados locked; superset inclui dependências
dev/Windows e AWS-LC vendorizado, não alegar composição ELF completa.
Docker allowlist ampliada só para coletor/suplemento; coleta no build e COPY
para runtime sem tokens/chaves. .deb instala copyright MIT e textos de
terceiros; testar hashes no payload e ciclo Ubuntu26 privado, sem serviços
do operador. Testes contratos devem cobrir essas novas entradas.

Somente fonte aceita commitada e clean: clone exato próprio, gate relevante
nesse commit e artefatos identificados por SHA/revisão. Docker Linuxamd64
Bookworm não root, sem latest, novas tags0.11.6 broker/legadoadmin e0.9.0
client. .debUbuntu26amd64, exporttar e manifest/checksums. GitHub prereleases
v0.11.6/v0.9.0 após push/tags; conferir assets reais e digests remotos Hub
lepinheiro100. Não sobrescrever tags/releases/arquivos já publicados.

Registros finais/matriz/checklist somente após PASS, limites claros: sem
MQTT5, produção/SLA/conformidade integral/ASAN/LibFuzzer/MSRV1.88 exato/arm64
ou novo teste Windows. Prompts e registros públicos nunca incluem secrets.
Falha de publicação não desfaz aprovação técnica mas deve ser informada,
sem dizer distribuído antes de verificação remota.

## Revisão1.1 — bytes de avisos antes de política Git

Inspeção confirmou core.autocrlf=true; suplemento valuable tem SHA pinado.
Adicionar packaging/notices/** -text a .gitattributes em ambos repos para
checkout não converter LICENSE original. Sem mudar bytes, licença ou fonte
de terceiro; hashes devem permanecer idênticos em clone/imagem/pacote.

## Revisão1.2 antes de corrigir coleta client

Dockerclient FAIL fechado: rumqttc0.25.1 não inclui LICENSE no crate. Metadata
Apache-2.0/repositorybytebeamio/rumqtt e .cargo_vcs_info.json confirmam revisão
f1e9e8d558783f942993046679cdf3c8c3a3d36b. API GitHub árvore completa dessa
revisão confirmou LICENSE raiz (11358bytes, blobd645695...), semNOTICE extra;
texto original recuperado por connector, não licença reescrita. Versionar
suplemento e SHA pinado, validar revisão/metadados antes de cópia, ampliar
allowlist somente pasta/LICENSE revisados e testes. Coreclient/MIT próprio
não são relicenciados; rumqttc conserva Apache2.0. Novo commit distribuição,
mesmo runtime0.9.0 ainda sem tag/release, clone exato atualizado e gate rerun.
OwnMIT EOL CRLF/LF é Gitcheckout: QA compara termos/copyright canônicos e
registra hashesraw; terceiros permanecem byte estrito, valuable -text preservado.
