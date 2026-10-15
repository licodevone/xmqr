# P111 rev1 — rotação de auditoria sem replay

2026-10-15. Entrada broker `fc4ebb1`, admin `a007307`, documento MQTT v4,
128 recibos append-only. A05 segue aberta porque um descarte ingênuo de IDs
permitiria repetir comandos antigos. Fase 5 global permanece aberta.

Introduzir `admin_epoch` durável e formato MQTT v5 (leitura v1..v4). Após
primeira rotação, IDs de novas mutações codificam época nos oito primeiros
hexadecimais; o ator recusa ID de outra época e mantém os IDs legados da
época zero em índice de aposentados limitado. Recibo contém sua época e,
para `audit_rotate`, hash e contagem do arquivo exportado. Não remover
recibos antes de validar hash/contagem exatos da auditoria atual.

Admin CLI `channel audit-rotate --archive NOVO_ARQUIVO_PRIVADO` lê páginas
operator, grava JSON canônico em arquivo novo0600, fsync arquivo/diretório,
envia hash/contagem/ID ao broker e mostra ID antes da mutação. Se o estado
mudar entre export e pedido, broker recusa sem limpar. Commit atômico no WAL
substitui recibos por um recibo de rotação, avança época e conserva índice de
IDs legados; timeout exige consultar receipt do ID antes de qualquer retry.
`audit-verify` offline confere hash do arquivo e o recibo de rotação por ID.

Negativos: archive público/symlink/preexistente, hash/count conflitante,
concorrência, capacidade cheia (rotação ainda permitida), replay de ID antigo,
falha WAL antes/depois de commit, restart e compatibilidade v4. Sem payload,
senha, token, tópico/client ID no arquivo. Gates Rust/integração com processos
isolados, documentação de rollback v5 e registro antes de aceite A05/A09.
