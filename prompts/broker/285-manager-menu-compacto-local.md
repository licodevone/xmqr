# P285 v1.0 — aplicar menu compacto do XMQR Manager no Windows

Entrada: broker c30c6cd, árvore limpa. O Manager em Program Files apresenta o
menu antigo da captura. O código do Manager 0.1.1 já contém o menu compacto P280.

Objetivo: aplicar a variante compacta no PC, preservando o significado dos
estados e deixando a ressalva de MQTT no tooltip. Reutilizar o código de
tools/windows-manager, sem redesenhar o menu nem mudar versões, serviços,
configuração, permissões ou dados. Atualizar apenas o executável do Manager,
com backup do original e reinício da bandeja como usuário normal.

Aceite: fmt, testes, Clippy e build release do Manager; validar inventário
somente leitura, identidade do binário ativo e continuidade dos três serviços.
Confirmar a largura na bandeja quando a sessão permitir. Registrar limitações.
Sem publicação, tag ou commit.

Revisão v1.1: o build não encontrou link.exe. Inspecionar o artefato local P280, confirmar os rótulos e o diagnóstico em modo somente leitura e não atribuir a ele um build novo.
