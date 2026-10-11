# P57 rev1 — código e notas ao lado de cada linha

Entrada: main627aab3, árvore limpa. Pedido: inserir linhas e o que cada uma faz.
Escopo: docs/code-guide.html e registroP57; sem modificar fontes de runtime.
Acrescentar coluna explicativa em todas as linhas dos26 arquivos Rust já
presentes no HTML. Descrever instruções, declarações, tipos, controle, chamadas,
comentários e delimitadores; explicar em contexto as operações conhecidas.
Separar notas estruturais de análise semântica humana: uma descrição extraída
da sintaxe não comprova efeitos internos de toda função chamada. Preservar
as explicações humanas já presentes e não alegar auditoria semântica integral.
Aceite: 11.769 linhas sem alteração e com nota não vazia; layout acessível,
busca e índice preservados, sem segredos. Validar contagem, texto das fontes,
HTML/âncoras e diff. Sem testes funcionais/release. Commit/push autorizados.

## rev2 — corrigir validação documental

Primeiro verificador usou Path('.') sem resolve: parent permaneceu relativo
ao broker e omitiu fontes do client. A comparação falhou por universo incorreto;
o JavaScript temporário não foi gerado e node informou arquivo ausente.
Resolver raiz absoluta antes de localizar repositório irmão e repetir comparação,
âncoras e sintaxe JS. Não alterar fontes nem alegar PASS na primeira tentativa.
