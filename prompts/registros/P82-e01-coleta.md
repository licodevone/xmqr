# P82 — coleta E01 segura e limitada

Data2026-10-13, Windows/PowerShell, PythonESP-IDF3.13.15/pyserial existente.
Prompt [P82v1.3](../broker/82-e01-coleta-segura.md), preparado/apresentado antes
das alterações, revisado antes das correções após falhas. Autorização: continuar
evolução por prompts com testes/MIT/commit/push e releases de marcos validados.
Base broker/admin0.11.4, HEADcaa68eed80b84c5880b8c96d9ed15e2b381c0579.
Main limpa no início; client0.8.1 não alterado e tarballs preexistentes preservados.

Skills xmqr-tests/security-review e orientações de implementação do projeto
aplicadas pelo agente principal; sem subagentes. Nenhuma alteração no núcleo,
manifests/lock, firmwareRust, admin/CLI, quotas/persistência, licença ou versões.

## Mudanças

- evidence.py: parser fechado ASCII/framing, ordem de milestones, veto a
  FAIL/reboot/duplicatas/incompleto, limites128markers/512bytes/64KiB/180s.
- Janela pós-STOP até1s, dentro do prazo, para detectar contradição posterior.
  Não é janela ilimitada nem prova de autenticidade do firmware.
- Monitor-only na COM especificada, reset normal e coleta sem flash/Docker.
  Fonte/identidade do firmware explicitamente desconhecidas; sequência positiva
  somente OBSERVED_MARKERS_ONLY. Não aceitar console como prova wire MQTT.
- Relatório schema2 em nome único/open exclusivo; não sobrescrever evidênciaP81.
- Finalização tenta stop/rm/volume de recursos criados pelo runner mesmo após
  outra falha; faz cleanup antes da escrita do relatório. Cleanup falho veta PASS,
  com códigos fixos; não guardar stderr/exceção sensível.

## Evidências e falhas corrigidas

| Verificação | Resultado real |
| --- | --- |
| Primeiros testes |35PASS; só testes sintéticos/guards, não MQTT |
| FAIL em chunk seguinte ao STOP | Negativo reproduziu PASS indevido, saída1/FAIL; P82v1.1 antes da correção |
| Correção da cauda |36testes PASS; cauda limitada até1s |
| Erros de relatório/cleanup |4novos negativos mock; total40PASS |
| Teto exato de bytes | Asserção extra reproduziu65664>65536, saída1/FAIL; P82v1.3 antes da correção |
| Suíte final | Python unittest discover40testes, saída0/PASS |
| Framing/encoding/secrets sintéticos | Prefixos/bytes inválidos/linhas longas/truncadas/fields desconhecidos recusados; nenhum texto sintético sensível no resultado |
| Fmt/inventário | cargo +esp fmt -- --check e license_inventory.py --check:0/PASS; grafo146pacotes preservado |
| Scan Windows read-only | alvo ainda invisível; sem imprimir SSID/redes alheias |
| Monitor real final | COM4/40s máximo; boot0.1.0 → WIFI_TARGET_NOT_FOUND_24GHZ → STOP; resultado FAIL_INITIAL_SLICE |
| Framing real final |0violações,11linhas descartadas sem conteúdo,416bytes lidos; ~4.31s |
| Flash/Docker nesta retomada | nenhum flash/container iniciado; somente reset normal/observação |
| Releases existentes | gh confirmou prereleasesv0.11.4 e v0.8.1 publicadas; não alteradas |

Observação final às07:53:34–07:53:38 America/Sao_Paulo; timestampsUTC no
[relatório sanitizado](../../docs/results/p82-e01-coleta-2026-10-13.json).
O comando separado do primeiro monitor retornou1 (falha Wi-Fi esperada), não
PASS. A execução final combinada também produziu FAIL_INITIAL_SLICE; não usar
exit0 do último comando Docker da célula como sucesso do monitor.

Build/Clippy do firmware e gatesRust111/54 anteriores não reexecutados: fontes
Rust/manifests/lock/binários não mudaram. Sintaxe Python testada por imports,
execução e testes. Não chamar mocks de campanha Docker/energia/MQTT física.

## Estado e limites

Coletor/guards aceitos, E01 físico PARTIAL/BLOCKED. O operador precisa tornar
a rede correta2,4GHz disponível ao ESP32; não adivinhar senha/SSID nem escolher
rede alternativa. Sem firewall/roteador/EIM/instalação, novos certificados ou
alteração dos backups. Credenciais e produtos com segredo continuam privados.

Console não é attestation nem prova de wire. Hash atual das fontes do host no
modo --flash é informação de execução, não vínculo criptográfico ELF↔Git;
observador independente e demais cenáriosE01 continuam necessários.
Fase2 não concluída, fase3 não iniciada. Sem nova tag/release/deb/Hub, pois
runtime0.11.4/0.8.1 permaneceu intacto. Compromisso de publicar novos marcos
validados preservado. Commit/push de fontes/registro sanitizado autorizados;
confirmar SHA real na entrega, não prever commit neste registro.
