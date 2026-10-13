# P85 — campanha física pendente e fechamento da fase2

2026-10-13, base0e42ee832029daf39e602c81218faa871d792100, main limpa;
broker/admin0.11.4, client0.8.1 independente, tarballs preexistentes intocados.
Pedido direto: executar os testes pendentes da fase2; autorização anterior de
backup/gravaçãoCOM4, prompts/MIT/testes/commit/push/distribuição mantida.
[P85v1.2](../broker/85-e01-campanha-pendencias.md) apresentado antes de fontes;
revisões antes das correções/novo escopo documental/publicação de evidência.

Skills xmqr-rust-mqtt/tests/security-review aplicadas pelo agente principal;
sem subagentes. Guiaram limites, casos negativos, TLS/ACL/identidades e separação
entre método de medição e alegação de produção. Client alinhado por C44.

## Implementação de teste

- Modo opt-in XMQR_E01_CAMPAIGN=1; anteriores preservados/compilados. Sem
  mudança em core/manifests/lock/versões. FirmwareRust próprioMIT/unsafe forbid.
- Caso privado novo/exclusivo: CA/board/observer vigentes preservados; servidor
  SANIP+DNS, perfilSANerrado, CA não confiada e cliente externo próprio. Mounts
  do broker não incluem chaves CA/board/observer/externo. ACLs concretas: board
  pub bytes/retained/Will, sub bytes/control; observer pub control somente;
  externo pub bytes/sub retained. Proibido e01/forbidden nunca foi concedido.
- Desassociação Wi-Fi da própria placa sem MQTT DISCONNECT → Will1024QoS1
  recebida pelo observer; mesma rede reconectada em até3tentativas/backoff1/2/4.
  Não alterou router/Wi-FiWindows/firewall. Não foi corte de energia/reset elétrico.
- Restart somente container próprio/mismo volume; MQTT recuperado, retained
 1024 replay a sessão nova, liveRETAIN0 e deletevazio/ausência2s+PING vivo.
  Ctrl8/31 retidos coordenam assinatura/recovery; controles não são negócio.
- QoS1 duplicado induzido pelo publisher externo fixture (mesmoID/DUP), recebido
  duas vezes com bytes válidos. Não é perda real de pacote nem exatamente-uma-vez.
- Mosquitto2.0.22 oficial por digest: subQoS2/replay/bytes1024 e pubQoS2 para MCU
  com bytes1024 conferidos. IDs/certificado/usuário externos próprios; senhas
  em configs privados XDG, nunca argv/env/log público. CLI exit0 confirmado por
  Docker.State.ExitCode, não apenas docker start -a. Nenhum payload cru publicado.
- CA/senha/ACL/SAN errados recusados com erro/desconexão observados; baseline
  e caminho correto recuperados, serviço vivo. SAN comCtrl30/ARMED, MCUespera8s,
  hosttroca/precheck≤6s e ACKcontrole≤1s exigidos; timeout sozinho não aprova.
  CallbackSDK seguro dá erro genérico: não há códigoTLS específico inventado.
- Memória com Vec.try_reserve_exact: uma alocação de cada vez, passos4096/
  teto196608, SDKabort-on-fail desabilitado/conferido. Registra capacidade
  contígua aproximada, NÃO total/min free heap/largest estatístico exato.
  Gatecurto:≥8192, quedaidle→final≤32768, outbox0; não prova vazamento longo.
- Parser fechado512bytes/64KiB/128markers/180s, sequência P85 obrigatória,
  métricas e14provas externas completas. Relatório privado único. Cleanup
  tenta jobs/container/volume/rede próprios mesmo após erros; preexistentes
  recusados. Nenhuma credencial/ELF/bin/target/flash/log completo publicado.

## Resultados reais

| Gate | Resultado |
| --- | --- |
| Primeiro unittest | Invocação usou cwd/start directory incompatíveis; falhou antes de importar testes; v1.1 corrigiu comando, não fontes |
| Suítehost Windows |94executados/93PASS/1SKIP (symlink sem privilégio), saída0 |
| Suítehost Ubuntu26/WSL |94PASS/0SKIP, saída0; usa pacote pyserial puroPython existente do venvESP Windows, não instalou dependência |
| Probe puroRust no host |2PASS; limites/primeira falha/quantização, saída0; não substitui mediçãoMCU |
| FixtureESP |fmt/crossbuild release locked/Clippy -D warnings PASS; campanha e compatibilidade retained anterior |
| Licençasfixture |146declarações/PASS; Cargo.lock intacto; SDK/toolchain mantêm licenças próprias |
| Backup/flash | duas leituras4MiB iguais; COM4/CH340; app1004848<1048576; bootloader/tabela reais/flash verificado |
| CampanhaCOM4 |PASS_PHYSICAL_CAMPAIGN, saída0,14provas externas,0violações,1169bytes/11linhas descartadas sem conteúdo |
| Wi-Fi |9048ms incluindo desconexão/teardown/backoff/associação/MQTT/pub; bytes após recuperação PASS |
| Brokerrestart |7869ms incluindo teardown/backoff/MQTT/pub; retained/restauração PASS |
| Memóriaprobe MCU |110592bytes em idle/wifi/restart/final; queda0; outbox0 checado no fim |
| Negativos |CA/senha/ACL/SAN rejeitados + caminho válido recuperado/serviço vivo PASS |
| Cleanup |0erros; jobs/container/volume/rede ausentes; firmware diagnóstico fica na placa, sem broker permanente |
| Broker regressões WSL |111RustPASS,fmt/Clippy/build/inventário PASS, saídas0 |
| Client regressões WSL |54RustPASS,fmt/Clippy/build/inventário PASS, saídas0 |
| Runtimes vs tags |git diff --quiet Cargo.toml/lock/src vs0.11.4/0.8.1:saída0/idênticos |
| Distribuição |debs/checksums nas releases e3digests remotos Hub conferidos; não retag/rebuild de mesmo runtime |

Execução física11:39:42–11:42:12 America/Sao_Paulo; timestampsUTC/hashes em
[JSON sanitizado](../../docs/results/p85-e01-campanha-2026-10-13.json).
Hashharness concatena basename+bytes na ordem do JSON; sourcehash host inclui
Cargo/lock/build/sdkconfig/configtarget/main/campaign/probe. Não é attestation
ELF↔Git, pcap descriptografado ou prova de commit futuro. cfgcampanha1 e build
privado selecionados; relatório guarda resultantes reais, não senha/chave.

## Aceite, limites e publicação

E01/campanha curta ACCEPTED combinado com P83/P84; softwareP80/C43 preservado e
regressões repetidas. **Fase2 ACCEPTED**, conforme checklist original, sem
inflar novo requisito de pcapTLS/attestation. Runner físico isolado mantém
phase2_closed=false porque não decide software; JSON/documentação combinados
registram fechamento após os gates. Isso não aprova fase3 ou produção/MQTT5.

Limitações: probe não é heap total, campanha longa/leak/statísticas exatas;
sem energia/reset elétrico, capturaTLS, teste físico de todos os caminhos de
retransmissão. QoS1 induzido é fixture. NegativosSDK não expõem detalheTLS exato.
Retainedupdate/replay vem de P84; livepublish/delete/restart e libMosquitto vêm
de P85. A ampliação de robustez permanece na fase3, não reabre gatecurto aprovado.

Código próprioMIT preservado, sem dependências novas; terceiros não relicenciados.
Sem firewall/router/GPIO/efuse/NVS/erase geral, serviços reais ou worktrees externos
alterados. Casos anteriores/backup/credenciais privados preservados. SDKalteração
somente configuração de falha de alocação; nenhum patch em SDK/libvendor.

Commit/push do broker e docsclientC44 após auditoria. EvidênciaJSONsanitizada
será anexada às releases existentes com adendo após confirmação, sem
clobber de asset diferente. Pacotes/digests/tags0.11.4/0.8.1 imutáveis, sem
novo runtime fabricado para teste. SHAreal do commit/asset confirmado na entrega,
não previsto aqui. Próxima fase apenas planejada, não iniciada nesta campanha.
