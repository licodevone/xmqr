# P256 — publicação dos Managers

Data: 2026-10-25, America/Sao_Paulo. [Prompt](../broker/256-manager-releases.md).
Pedido explícito de commit/push, tags e releases após P255. Versões previstas:
Manager Windows 0.1.1 e Manager Ubuntu 0.1.0; tags próprias, prereleases e sem
alterar latest. A homologação completa de UAC/polkit/desktop continua pendente.

## Entrada e escopo

Base 654410c em main, alinhada com origin/main. Mudanças P254/P255 revisadas,
client/admin sem alterações. Históricos anteriores de 22–24/10 ficam locais;
o histórico de 25/10 e documentos deste trabalho acompanham a publicação.
Nenhum serviço real, instalação ou ACL será modificado por esta publicação.

## Fonte, tags e releases

Commit de implementação/publicação:
[`2aa4279d9b10ec474d65ca4afe262f03e61c4dc6`](https://github.com/licodevone/xmqr/commit/2aa4279d9b10ec474d65ca4afe262f03e61c4dc6),
enviado a origin/main sem force. Revisão do diff e de assinaturas de segredos
do conteúdo staged passou. Manifest e lock do Manager Windows estão em 0.1.1;
Ubuntu permanece em 0.1.0. LF do launcher Linux/desktop é fixado em .gitattributes.

Tags anotadas, enviadas atomicamente e conferidas no remoto:

- `manager-windows-v0.1.1` → `2aa4279d9b10ec474d65ca4afe262f03e61c4dc6`.
- `manager-ubuntu-v0.1.0` → `2aa4279d9b10ec474d65ca4afe262f03e61c4dc6`.

Releases publicadas com `--verify-tag --prerelease --latest=false`, sem substituir
anexos ou tags existentes:

- [Manager Windows 0.1.1](https://github.com/licodevone/xmqr/releases/tag/manager-windows-v0.1.1):
  MSI, ZIP portátil com executável/licença/notices, build-provenance.json e SHA256SUMS.txt.
- [Manager Ubuntu 0.1.0](https://github.com/licodevone/xmqr/releases/tag/manager-ubuntu-v0.1.0):
  .deb, build-provenance.json e SHA256SUMS.txt.

Consultas remotas confirmaram ambas como publicadas (`isDraft=false`) e
pré-releases (`isPrerelease=true`). Os pacotes têm origem no SHA exato acima.

## Validação real

[CI Desktop Managers 40254445323](https://github.com/licodevone/xmqr/actions/runs/40254445323)
concluiu com sucesso nos dois jobs para o SHA exato:

- Windows: fmt, 20 testes, Clippy sem warnings e build release.
- Ubuntu26.04: 29 testes, smoke GTK/D-Bus/Xvfb com reinício geral simulado,
  arquivos desktop, build .deb e smoke de modos/ownership/launcher/import isolado.

Localmente, os gates Windows 0.1.1 também passaram. MSI construído de worktree
destacada limpa do mesmo commit, com manifest `source_dirty=false`, ícone
nativo intacto e notices de 79 dependências. A inspeção somente leitura das
tabelas de interface do MSI passou (sem instalação).

Tentativa de build local Ubuntu via WSL26.04 falhou por timeout de conexão
do WSL (`0x8007274c`), sem produzir pacote. Foi usado diretamente o artefato
`xmqr-manager-ubuntu26` produzido e aprovado pela CI do commit exato, baixado
com `gh run download`; não se reaproveitou o candidato P255 anterior.

Depois da publicação, todos os anexos foram baixados novamente do GitHub.
Os SHA-256 de todos os arquivos listados em cada SHA256SUMS.txt coincidiram.
Também foram conferidos o SHA/estado limpo/CI do build-provenance.json e o
hash do executável dentro do ZIP portátil, além da presença da licença.

| Artefato publicado | SHA-256 |
| --- | --- |
| Windows MSI 0.1.1 | `cd193c74e37267e66d14a63cd52d3cadb147f6e21e39071829657e52238e3f7f` |
| Windows ZIP portátil 0.1.1 | `481bbbdb38f268c475e44013fc5f60476296be6a5f95c0585b734322844a60e5` |
| Executável Windows no ZIP | `3c4e11e1ae9e67e7a01d632d84d6dbf69addda4a85e2202ae0bc12c1e7c5943e` |
| Ubuntu .deb 0.1.0-1 | `e2404c621b5bb152508653972285b03cb041334daf5b041dcd1d9a35812f687a` |

## Limites e preservação

O aceite desta publicação é de fonte, testes e pacotes experimentais. UAC,
polkit/GVfs admin, controle dos serviços reais, instalação/upgrade/rollback,
boot/login/Wayland e DPI continuam sem homologação completa. Os limites constam
das notas e da proveniência dos anexos. Nenhum Manager foi instalado/atualizado
no host; serviços e ACLs reais não foram alterados. Os três produtos mantêm
suas versões; client/admin não tinham mudanças para publicar nesta tarefa.

A CI geral do broker também foi disparada automaticamente pelo push. Na
conferência de publicação, o job ubuntu-package havia passado e o job rust
continuava em integrações; não foi usado como evidência de conformidade dos
Managers. A CI específica acima é a aprovação do SHA marcado pelas duas tags.

Documentos/históricos anteriores de 22–24/10 permanecem locais e intactos,
fora dos commits desta tarefa. O registro final e o chat são publicados por
commit documental posterior; as tags continuam fixadas no commit validado.
