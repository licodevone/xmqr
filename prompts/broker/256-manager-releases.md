# P256 — publicação dos Managers

Versão 1.0, 2026-10-25, America/Sao_Paulo. Pedido explícito do usuário:
"faça o commit/push e crie as tags e releases". Autoriza versionamento,
commit/push e pré-releases dos Managers implementados em P255, com os limites
de UAC/polkit/desktop já informados. Não autoriza instalar ou controlar os
serviços reais nesta publicação.

Entrada: main/HEAD 654410c, alinhado com origin/main; P254/P255 e Manager Ubuntu
locais, sem commits; históricos anteriores de 22–24/10 preservados fora do
escopo do commit. Repositórios client/admin limpos, sem alterações desta tarefa.

Objetivo: publicar tags imutáveis manager-windows-v0.1.1 e
manager-ubuntu-v0.1.0, com instaladores derivados do commit exato, checksums,
notas, fonte e CI dos Managers aprovadas. Releases experimentais marcadas como
prerelease, sem alterar latest. Windows sobe 0.1.0→0.1.1 para permitir upgrade
MSI; Ubuntu mantém a versão inicial 0.1.0. Versões broker/client/admin intactas.

Escopo: manifest/lock do Windows Manager, notas de release, versionamento,
registro P256, publicação do código/documentos P254/P255, workflow específico,
histórico desta conversa. Não publicar credenciais, dados privados ou artefatos
de commits diferentes. Não incluir mudanças locais anteriores sem relação.

Fluxo: revisar diff e segredos; testes locais proporcionais; commit/push;
aguardar CI Desktop Managers do SHA exato; checkout/worktree limpa desse SHA;
construir MSI/.deb com proveniência e notices; verificar versões, pacotes e
hashes; tags anotadas e push sem force; criar duas prereleases com --verify-tag
e --latest=false; baixar anexos e confrontar SHA-256. Registrar resultados reais.

Aceite finito: fonte/testes/pacotes e publicação verificáveis. Não equivale a
homologação completa de UAC/polkit, serviços reais, reboot/login/Wayland ou
instalação/upgrade no desktop. Falhas exigem correção e novo commit/CI antes da
tag. Tags existentes não podem ser movidas; nunca substituir anexos publicados.
Sem avanço de protocolo, instalação no host ou release dos três produtos.

Revisão v1.1: fixar LF no launcher Linux sem extensão e nos arquivos desktop,
para preservar executabilidade ao empacotar a partir de checkout Windows com
core.autocrlf=true. Validar também no pacote reconstruído da worktree limpa.
