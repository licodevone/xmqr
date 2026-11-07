# P257 — atualizar o Manager instalado no Windows

Versão 1.0, 2026-10-25, America/Sao_Paulo. Pedido explícito:
"prossiga com a atualização" após conferência dos comandos conjuntos.

Entrada: HEAD 7c7a989, histórico de chat local modificado e preservado.
Manager instalado 0.1.0, em C:\Program Files\XMQR\Manager, processo 25472.
MSI 0.1.1 de P256 disponível em dist/releases/p256-verify/windows;
SHA-256 esperado cd193c74e37267e66d14a63cd52d3cadb147f6e21e39071829657e52238e3f7f.
Gates do crate Windows já reexecutados nesta sessão: 20 testes, fmt e Clippy PASS.

Objetivo: substituir a instalação do Manager por 0.1.1 e abrir a bandeja
com comandos Iniciar todos, Parar todos e Reiniciar todos.
Escopo: atualização MSI do Manager, reinício de seu processo, conferência
somente leitura do inventário/serviços, prompt, registro e chats.

Procedimento: conferir hash do MSI; registrar estado dos serviços e opções
de atalhos; encerrar apenas o processo Manager cujo caminho corresponde ao
instalado; aplicar MSI com licença MIT existente, preservando atalhos,
sem reinício automático do Windows; verificar saída MSI, versão no registro,
hash do executável e probes --version/--help/--diagnose capturados por pipes;
abrir Manager atualizado e inspecionar menu se desktop acessível.

Aceite: MSI retorna sucesso (0 ou 3010, reportando reinício se solicitado),
registro aponta 0.1.1, executável corresponde ao publicado em P256,
processo da instalação está ativo; controles gerais presentes no help/menu.
Comparar estados de serviços antes/depois sem comandá-los. Não executar
controle geral apenas para validar atualização. Não alterar produtos,
configurações, credenciais, dados, ACLs, versões, fonte ou tags/publicações.
Registrar evidências reais e limitações em prompts/registros/P257-*.md.
Falha de upgrade deve ser registrada antes de revisar procedimento e corrigir;
não remover a instalação nem aplicar fallback destrutivo automaticamente.

## Revisão 1.1 — token da bandeja após atualização

MSI retornou 0 e versão/hash foram conferidos. A reabertura direta herdou
o token administrativo do agente, enquanto Explorer está sem elevação.
Reabrir somente o Manager através do Shell do desktop, com token normal;
conferir TokenElevation do processo sem alterar permissões ou serviços.
O menu da bandeja não é exposto como janela pelas APIs de Computer Use
disponíveis; declarar esse limite e usar os probes instalados como evidência.
