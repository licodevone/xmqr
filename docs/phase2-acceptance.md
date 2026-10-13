# Fase 2 — aceite separado por componente

Atualizado2026-10-13, P80/C43/P81/P82/P83/P84/P85 e C44.
Broker/admin0.11.4 e clientruntime0.8.1 preservados. **Fase2 ACCEPTED no escopo
definido: softwareP80/C43 + campanha física E01/P83/P84/P85.**
Não significa conformidade integral, produção ou fases seguintes executadas.

| Responsável | Entrega | Estado |
| --- | --- | --- |
| Broker | P62baseline e P72QoS/fan-out/mTLS | PASS histórico |
| Broker | Admissão1/8/32/64, N+1 e vaga reutilizada | PASS P80,24cenários |
| Broker | Handshake silencioso e liberação | PASS P80,6cenários |
| Broker | FilaN/N+1 QoS1/2, restart/drain, outros peers | PASS P80,24cenários |
| Broker | Não leitorQoS0 TCP/mTLS e vaga reutilizada | PASS P80,6cenários |
| Broker | ShutdownTLS limitado e regressões de ator/transporte | PASS,111testesRust e fmt/Clippy/build/inventário |
| Broker | Avaliação de quotas por identidade | Decisão ADR0006; isolamento multitenant não implementado |
| Client/broker | Mosquitto2.0.22 externo mTLS/bytes/QoS/retained/Will/sessão/negativos | PASS C43,59cenários |
| Client | Regressões de runtime | PASS54testesRust; sem mudança de CLI/versão |
| Todos/software | Método, RAM/CPU/p50/p95/p99, limitações | P80 e JSON sanitizado |
| ESP32 DevKitV1 | COM4/chip/backup/firmware/boot reais | PASS parcial P81; firmware diagnóstico na placa |
| ESP32/host | Coleta restrita e atualização privada/atômica da senha | P83:54PASS/1SKIP Windows;15PASS sync WSL, incluindo symlink real |
| ESP32 DevKitV1 | Wi-Fi/IP/SNTP/mTLS e loopback1024bytes/QoS0/1/2 | PASS primeira fatia P83, placa real; positivos, não todos os gates |
| ESP32 DevKitV1 | Retained create/update/replay/delete, observer próprio wire independente | PASS P84;1024bytes/replay RETAIN1/QoS1, zero byte delete/janela2s+PING vivo |
| ESP32/host | Novos negativos e compatibilidade do fixture | P84:82PASS/1SKIP Windows;64PASS subset WSL; build/fmt/Clippy em ambos os modos |
| ESP32 DevKitV1 | Will, reconexãoWi-Fi/broker, retained restart/live/delete, duplicataQoS1 | PASS P85, provas físicas/wire |
| ESP32 DevKitV1 | Mosquitto2.0.22/QoS2 nas duas direções,1024bytes | PASS P85, cliente terceiro por digest/IDs próprios |
| ESP32 DevKitV1 | CA/senha/ACL/SAN errados + caminho válido recuperado | PASS P85, rejeição observada e serviço vivo |
| ESP32 DevKitV1 | Memória e recuperação limitadas | Probe110592bytes estável;Wi-Fi9048ms/broker7869ms; não heap total/vazamento longo |
| ESP32/host | Gates do fixture e cleanup |94testesWindows/1SKIP;94WSL/0SKIP;2Rustprobe;fmt/build/Clippy/inventário PASS;0erros cleanup |

[CapacidadeP80](performance-pressure.md) · [Dados](results/p80-pressure-2026-10-13.json) ·
[ADR](architecture/adr-0006-identity-quotas.md) · [ChecklistE01](esp32-phase2-checklist.md) ·
[ClientC43](https://github.com/licodevone/xmqr-client/blob/main/docs/phase2-acceptance.md).

Os relatórios versionados foram gerados antes do commit, com HEAD de entrada,
hashes do harness/binários e imagesIDs. Não são prova de commit futuro.
Artefatos de correção0.11.4 exigiram clone limpo, repetição dos gates pertinentes,
.debUbuntu26amd64/lifecycle e imagens broker/adminBookwormamd64, checksums,
tag e digests nos anexos. As evidências P80 anteriores ao commit não provam
publicação por si mesmas; v0.11.4 foi publicada posteriormente. P81 não muda
runtime, tag ou artefatos existentes.

SomenteE01real + software aceito permitem ACCEPTEDfase2. Uma release de correção
pode ser aceita antes da placa, sem representar encerramento da fase ou produção.

P85 forneceu esse gate físico e fechou o aceite combinado. Runtimes/manifests/
lock/src dos dois projetos foram comparados às tags0.11.4/0.8.1: idênticos.
Artefatos .deb existentes conferidos nas releases; três digests do Hub remoto
mantidos. Sem novos executáveis ou retag. [P85](../prompts/registros/P85-e01-campanha.md),
[dados](results/p85-e01-campanha-2026-10-13.json). Cliente alinhado por C44.

A memória é capacidade contígua aproximada por Vec.try_reserve_exact (passos4096/
teto196608), não estatísticas exatas do heap. NegativosSDK são callbacks genéricos,
sem inventar códigoTLS específico. Recusa exige falha observada, baseline válida
e serviço vivo; timeout sozinho não aprova. Restam campanhas longas/fuzzing/
energia e demais itens da fase3+, não pendências do gate curto aqui aprovado.

## Histórico — os bloqueios abaixo retratam os checkpoints anteriores

P81 elimina o bloqueio histórico da porta, não o gate completo. Fixture
independente compilado/Clippy/fmt,8testes de segurança do runner e inventário
de licenças PASS. Pré-check host mTLS PASS; não equivale a MQTT na placa.
Rede configurada ausente no scan ESP32 e na consulta Windows; não alterar
roteador/firewall nem tentar outra rede automaticamente. Evidência em
[P81](../prompts/registros/P81-esp32-e01.md). Sem avanço para fase3 ou nova tag.

P82 repetiu observação serial sem gravar firmware ou iniciar containers.
O alvo Wi-Fi continuou ausente; MQTT físico NOT_RUN. Códigos de erro e parser
fechado não substituem observador wire independente, heap ou demais cenáriosE01.
As versões/releases/pacotes permanecem0.11.4/0.8.1; não há novo binário a publicar.
[RegistroP82](../prompts/registros/P82-e01-coleta.md).

P83 resolve a associação inicial: senha corrigida sincronizada sem mudar MQTT,
certificados ou ACL; build observa config/PEMs privados. Primeiro run ainda
parou no scan separado, apesar de alvo visível no Windows. Após promptv1.1,
retirou-se esse pré-gate: `wifi.connect()` faz sua própria busca do AP configurado.
Segundo run PASS_INITIAL_SLICE: Wi-Fi/IP, horário, mTLS e1024bytes/QoS0/1/2.
O scan anterior não prova ausência real da rede; causa exata não demonstrada.

Sem scan externo, mudança de rede/firewall, certificado novo, NVS ou erase geral.
Container/volume próprios removidos, backup preservado e firmware diagnóstico
permanece na placa. Sem broker de laboratório permanente. Não avançar fase3.
[RegistroP83](../prompts/registros/P83-e01-wifi.md) e
[dados sanitizados](results/p83-e01-wifi-2026-10-13.json). Bloqueios P81/P82 acima são históricos.

P84: placa criou/substituiu/apagou retained; assinantes novos com certificado/
usuário distintos verificaram flag, QoS e bytes do último valor. Observer
wire Python não usa codecRust/ESP-IDF, mas é fixture própria, não libmosquitto.
Entregas dos três loopbacks foram0/1/1 por assinaturaQoS1; não atestar handshake
QoS2 MCU↔broker a partir delas. Console sozinho ou wire sozinho não aprovam.
Certificados/políticas de laboratório separados, mounts sem chave de dispositivo/
observer/CA, recursos próprios removidos. Sem alteração de runtime/versões.
[RegistroP84](../prompts/registros/P84-e01-retained.md),
[dados](results/p84-e01-retained-2026-10-13.json). Não avançar fase3.
