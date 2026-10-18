# P231 — inventário e triagem normativa MQTT 5

Prompt: [P231 v1.5](../broker/231-auditoria-normativa-mqtt5.md).
Data: 2026-10-18. Autorização: continuar auditoria, gerir modelos por tarefa,
commit/push do trabalho aceito e tags/releases quando justificadas.

## Entrada, arquivos e limites

Broker limpo em `76d3cbdf48b8c6ab1ac74b29fc7bb00eb16ad1ac`, igual a origin/main
verificado por ls-remote. Runtime 0.43.0. Nada do client/admin foi editado ou
incluído. Não acessar segredos/estado operacional, não iniciar serviço e não
alterar ESP32, firewall, instalação, configuração global ou versões existentes.

Arquivos: prompt/registro P231, extrator e testes Python, catálogo JSON, guia de
auditoria, link em mqtt5-status e CI offline dedicada. Nenhuma alteração em
`src/`, Cargo.toml, Cargo.lock ou Dockerfile. Não há migração/dependência nova.
MIT autoral preservada; a norma OASIS não foi redistribuída nem relicenciada.

## Gestão de modelos efetivamente utilizada

- `p231_evidence_luna`: `gpt-6-luna`, `high`, contexto novo delimitado;
  leitura de código/testes existentes e revisão independente do extrator.
- `p231_normative_sol`: `gpt-6.1-sol`, `high`, contexto novo delimitado;
  interpretação normativa dos três candidatos, anomalias da fonte e revisão final.
- Coordenador: integração, implementação da ferramenta e execuções abaixo.

Os dois agentes trabalharam somente em leitura; nenhum executou testes ou
publicou arquivos. Não houve troca do modelo principal da conversa nem uso de
Astra nesta fatia. Subagentes não receberam credenciais ou payloads reais.

## Fonte e achados

HTML oficial OASIS OS 2019 baixado somente para
`../.artifacts/p231-mqtt-v5.0-os.html` (fora do Git): 1.436.047 bytes,
SHA-256 `41116bcf54bc9b9ee72a425406293efda60fb40741e7d1512b87f51a46fa499c`.
Meta declara windows-1252. Extração estrita: 252 IDs, 501 ocorrências;
capítulos 1/2/3/4/6: 5/7/175/61/4. Isso não é número de MUST aplicáveis,
porcentagem de cobertura ou evidência de conformidade global.

Anomalias preservadas: IDs literais 4.2-1/4.2.0-1 distintos, token truncado
T-3.2.2-8] no corpo e condição invertida no resumo não normativo para 3.3.1-10.
Não corrigidos por regex; julgamento exige texto principal e §7.

Subscription Identifier zero e Topic Name vazio sem alias: inspeção confirma
erro/encerramento e ausência de diagnóstico específico em caminhos genéricos;
§4.13.1 separa MUST fechar de SHOULD enviar DISCONNECT. Não foi reproduzida
violação obrigatória. Quotas locais exigem classificação por §4.13.2, não
inferência universal de 0x95. Âncoras/casos e pendências no
[guia](../../docs/conformance/mqtt5-normative-audit.md).
Revisão final independente Sol: nenhum problema material no guia/extrator;
não alegou execução de testes. Catálogo inteiro segue UNREVIEWED por papel.

## Execução real e falhas preservadas

Ambiente Windows/PowerShell, Python 3.13; validação adicional Ubuntu-26.04/WSL,
Python 3.14.4, mesma árvore montada, sem builds nem estado MQTT.

1. Sondagem inicial com decode UTF-8: **FAIL**, UnicodeDecodeError byte0xb7
   posição51173. Prompt v1.1 antes de aceitar apenas charset declarado válido.
2. Primeira suíte sintética: **11/11 PASS**, 0,017s, exit0. Geração do catálogo:
   exit0, 252 IDs/501 referências, NOT_AUDITED.
3. Revisão Luna identificou charset em comentário/corpo, conflitos de charset,
   chaves JSON duplicadas e bool confundido com inteiro. Prompt v1.2 e testes
   negativos antes da correção: **RED**, 15 métodos/5 falhas reportadas
   (duas são subcasos do mesmo método), 0,023s, exit1.
4. Prompt v1.3 precedeu a correção. Primeira tentativa teve SyntaxError por
   parêntese incorreto na linha179 de json.loads: suíte/check exit1 antes de
   executar. Prompt v1.4 registrou erro e precedeu correção de sintaxe.
5. Suíte corrigida: **15/15 PASS**, 0,022s, exit0. Check da fonte oficial exit0
   com mesmo hash/contagem; não foi necessário regenerar o catálogo.
6. Prompt v1.5 incluiu CI offline e teste de consistência do catálogo versionado.
   Windows: `python scripts/test_mqtt5_normative_inventory.py`, **16/16 PASS**,
   0,025s, exit0. Ubuntu/WSL: mesmo teste, **16/16 PASS**, 0,016s, exit0.
7. Windows e WSL: `mqtt5_normative_inventory.py --source <HTML local> --check
   docs/conformance/mqtt5-normative-audit.json`, **CHECK_PASS**, exit0.
   Significa extração coincidente, não conformidade do produto.
8. AST dos dois scripts PASS; workflow YAML parseado com BaseLoader local,
   gatilhos/permissions/comando offline conferidos; diff --check PASS.
   Links locais conferidos (registro criado após a primeira checagem).

Não foram repetidos testes Rust, interop, serviços, fuzzing ou hardware para
esta mudança de inventário. Os PASS históricos da fase6 não foram atribuídos
a esta execução. CI remota desta mudança ainda não executada neste registro
pré-publicação; consultar o resultado do commit publicado, sem presumir PASS.

## Aceite e distribuição

**Aceita a base da auditoria e sua triagem inicial; auditoria global pendente.**
Contagem não elimina revisão semântica, regras não numeradas, avaliação por
papel e evidência wire. Próximo recorte delimitado: capítulos1/2 e textos
associados. Nenhuma fase adicional foi marcada como concluída.

Commit/push dos arquivos próprios estão autorizados. Não criar versão/tag,
release, .deb ou imagem Docker artificiais: runtime não mudou. Preservar tags,
releases e latest anteriores. Futuro desvio funcional terá prompt/gates e
distribuição próprios. Não se anunciou certificação ou produção.
