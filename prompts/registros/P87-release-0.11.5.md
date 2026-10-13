# Registro P87 — publicação concluída

2026-10-13. Autorização contínua do mantenedor, promptP87 criado antes do bump
e publicação. Código/P86:3606ede844210997fa733408855099535145ac48, commit/pushmain
concluídos; tag anotadav0.11.5, objeto b461ffd1ae914bbcde94f5d5cde0f7fb0053fd90,
aponta para esse commit (local e remoto conferidos). O follow-up documental
não move tag nem recompila/substitui os artefatos publicados.

[Release experimental](https://github.com/licodevone/xmqr/releases/tag/v0.11.5)
publicada, draft=false/prerelease=true.18anexos: .deb, duas imagens exportadas,
manifesto, quatro relatórios/aceite, digests de registry e seus checksums.
Todos os18tamanhos e SHA256 conferidos contra os digests da API GitHub.

## Gates do commit exato

Clone limpo Linux em /tmp, Rust1.99/Ubuntu26amd64/WSL:fmt/test123/clippy-Dwarnings/
buildreleasebins/inventário PASS exit0. Contrato distribuição Python5PASS.
Reutilizado cache Cargo, não fontes/estado privado. Clone Git independente
limpo Windows serviu apenas ao contexto Dockerallowlist. Versão real5 e labels
do commit verificados no build e pelo exportador. Fila/injetorcfg(test) não
existem como configuração/runtime dos binários distribuídos.

Client0.8.1:54Rust/fmt/clippy/build/inventárioPASS; nenhuma edição, novo build
de distribuição, commit/tag ou troca de pacote/imagem do client. Seus dois
artefatos0.7.1 não rastreados permanecem intactos.

Docker:verify_docker PASS (mTLSpub/subQoS1, bytes/retain, SIGTERMexit0, retained
restart, CA/senha inválidas); verify_admin_image PASS (não contém broker,
lockativo recusado, backup/verify/restoreoffline e destino existente recusado).
Matriz externa C43 reexecutada:59PASS com Mosquitto2.0.22 fixado porimageID,
broker0.11.5 e client0.8.1. Não equivale a MQTT3.1.1 exaustivo.
ClientsMosquitto nativos ausentes noWSL: gate nativo BLOCKED; alternativa
Docker real executada, não instalação automática de ferramenta no host.

build_deb.py PASS, aviso usr-merge dpkg-shlibdeps sem erro. Package lifecycle
emUbuntu26 descartável PASS: broker0.11.4-1 ->0.11.5-1 e pacotesclient existentes
0.8.0-1 ->0.8.1-1, rollback dos dois, remove/purge. Configuração/dados/credenciais
simulados e permissões preservados, units verificadas e sem auto-enable.
Não testou systemd comoPID1 nem alterou a instância instalada do operador.

## Artefatos e digests

- xmqr-broker_0.11.5-1_amd64.deb:2.369.996bytes,
  SHA256 fdef9543aa4ef2a45095dca6dd50da478365c984fbede74bad2fb8fa615335d4.
- Dockerbrokerexport:34.793.727bytes,
  SHA256 6a0d06dac9874a8fb3c8f1236c949f0e1afc07dea94ebea86225ccda49f1c8de.
- Dockeradminexport:31.819.339bytes,
  SHA256 160515af44ad0bd137089cf17c68e7e0e2213abc969f4af6e2ea56fb6177b40c.
- Hub lepinheiro100/xmqr-broker:0.11.5:
  sha256:bd12e795a9f3817a5c3c0074bdf4f5ecc8c139114dd51cd501912cc836ef9dc1.
- Hub lepinheiro100/xmqr-admin:0.11.5:
  sha256:ec599e6e5c170d4adcf4cf7dfbc2b8653f8139bebf096ff9bc255e2425084a72.

push de ambas exit0; consulta remota independente confirmou os dois índicesOCI
linux/amd64 e attestations. Preflight de ambas as tags era notfound; nenhum
overwrite/latest ou mudança de tag antiga. Contexto e relatórios sem dados reais.

## Falhas intermediárias e limites

A primeira tentativa de cloneLinux com variável na chamadaWSL perdeu a variável
na passagem entre shells e tentou /xmqr; falhouPermissionDenied sem criar clone.
Substituída por mktemp/caminhos explícitos, clones limpos confirmados. AvisoHTTP2
inicialDocker não impediu build; todos os códigos finais0. O scriptpackage foi
copiado do blobGit comLF para evitarCRLF de checkoutWindows, conteúdo idêntico.

Recursos de testes p63/c43/p78admin/package removidos pelos próprios harnesses;
listas de containers/volumes/redes correspondentes conferidas vazias. Preservados
artefatos públicos e clones de provenance; sem excluir dados/repositórios do usuário.
Não alterou serviço real, firewall, router, Wi-Fi, certificados reais ou ESP32COM4.

MIT própria, dependências, quotas e formatos mantidos. Apenas Ubuntu26.deb e
DockerBookwormlinux/amd64 homologados neste recorte. Sem disco físico/energia,
Ubuntu24/arm64/Windowsbroker/MSRV1.88 exato/MQTT5 ou produção. Fase3parcial:
próximo recorte B07fuzzing, seguido de prolongados/matrizB08 e C07.
