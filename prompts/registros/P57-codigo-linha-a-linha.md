# P57 — notas ao lado do código

Base627aab3; árvore limpa. Promptrev1 antes da atualização; rev2 antes de
corrigir o verificador documental. HTML mantém fontes da baseline anterior.
Acrescentadas 11.769 notas lado a lado nos26 arquivosRust broker/client:
número, fonte e explicação de instrução/estrutura. Inclui linhas vazias,
comentários, atributos, declarações, chamadas, controle, testes e delimitadores.
Explicações humanas de módulos/configuração/startup preservadas.

Notas assistidas por análise textual, não análise completa de tiposRust:
709 linhas possuem nota de continuação estrutural. Métodos dependentes do
receptor e chamadas sem semântica específica conhecida são descritos como
tais. Não afirmar auditoria humana linha por linha nem efeitos não verificados.

Primeira validação falhou: raiz relativa calculou destino errado do client;
JS temporário não gerado causou arquivo ausente no node. Após rev2, raiz
absoluta resolveu o problema. Validação finalPASS: todas11.769 linhas iguais
às fontes, notas não vazias, IDs únicos e âncoras válidas; node --checkPASS e
git diff --checkPASS. Não repetidos testes funcionais. Sem tag/release.
