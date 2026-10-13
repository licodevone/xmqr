# Registro P80 — capacidade e correção de shutdownTLS

Pedido: finalizarfase2; commit/push e marcos aceitos autorizados. Data2026-10-13.
Prompt80rev1.7. Base4e199b2, clientbc94bd0. Branches codex/fase2-capacidade.
Preservadas duas archivesclient0.7.1 e conteúdo do curso.

Execução Linux/Ubuntu26WSL/Rust1.99:
fmt/test/clippy-Dwarnings/buildrelease/inventário PASS;111testesRust,
incluindo2novosator e2novostransporte. Pythonpressure5 e distribuição5 PASS.
Campanha P80 revisada60cenários/3repetições/2transportes PASS.
Hashes, RAM/CPU/latência, versão e HEAD de entrada no JSON versionado.
C43base47 e ampliação59cenários externos PASS, referênciaMosquitto2.0.22
pinada porimageID/digest; runtimeclient0.8.1 com54Rusttestes PASS.

Falhas/revisões antes das correções: patchcontexto; setterstore inexistente
identificado antes da compilação; Sampler poderia acessar/proc apósshutdown
identificado antes da campanha; mTLSnãoleitor timeout reproduzido2vezes.
Descoberta: unregister remove sessão, shutdownTLS/flush sem deadline retém
tarefa/permit. Patch3s comprovado no socket não leitor e nova vaga.
Revisão adicional reforçou cleanup/paralelismo/vaga e nome da latênciaQoS2.
Tentativa de gerar documentos falhou no templateJS/backtick sem aplicar arquivos;
segunda geração feita com texto escapado, sem mudança de runtime.

Compatibilidade: nenhuma mudança de wire/WAL/ACL/quotas; dependências inalteradas,
MIT preservada. Ver src/transport/mod.rs e regressões emrouter.rs.
Review: fix é async timeout + drop, sem bloqueio extra ou logs de segredos.
Durabilidade antes deACK intacta; TLS padrão/CA/SAN/fingerprint intactos.

GateE01 físico BLOCKED/NOT_RUN: inventárioWindowsSerialPort e dispositivos
ttyUSB/ttyACM noWSL vazios. Não flasheou placa, instalou tooling, mudou
firewall ou iniciou serviço instalado. Recursos de testes exclusivamente próprios.
Fase2global permanece PARTIAL/BLOCKED; software aceito; fases3–9 não iniciadas.

Registro anterior ao commit: não inventar seuSHA. Marco patch0.11.4 só é
publicado após gates finais do commit limpo e pacote/Docker. Anexos finais
identificarão commit, digests e reexecução; tag antiga/client/latest imutáveis.
