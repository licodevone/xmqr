# Icones Windows - P246

broker.png e o logotipo XMQR enviado pelo usuario, preservado sem alteracoes
artisticas. Admin, Client e Manager foram gerados como variantes visuais da
marca e ajustados a pedido: nome do aplicativo grande, XMQR pequeno embaixo.
Os PNGs possuem transparencia; o fundo preto de algumas visualizacoes nao faz
parte dos arquivos.

`scripts/convert_windows_brand_icons.ps1` converte os PNGs para ICO com nove
resolucoes (16,20,24,32,40,48,64,128,256), ignorando somente padding totalmente
transparente ao ajustar cada quadro. Tambem gera o RGBA 32x32 da bandeja em
`tools/windows-manager/assets/manager.rgba`. Nao redesenha a marca.

MSIs usam o ICO correspondente em atalhos e ARPPRODUCTICON.
`scripts/set_windows_executable_icon.ps1` aplica recursos nativos somente em
copias PE sem assinatura, conferindo a integridade do codigo/dados. A bandeja
usa o Manager, indicador verde quando todos os servicos observados executam,
cinza/apagado quando parados/ainda nao iniciados, amarelo em estados mistos
ou transicao e vermelho quando falha real/consulta indisponivel.
