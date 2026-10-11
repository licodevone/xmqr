# P56 rev1 — explicação dos prompts, arquivos e código

Entrada: HEAD b577dd0, árvore limpa; P55 preparado, não implementado.
Pedido: explicar com máximo detalhe possível o que os prompts construíram,
papel dos arquivos e código. Escopo documental, sem executar P55.
Criar docs/code-guide.md: catálogo dos prompts broker, evidências e limites;
mapa dos arquivos Rust broker/client; fluxo de execução; leitura detalhada de
configuração e startup. Não afirmar causalidade histórica sem registro.
Adicionar índice reproduzível de arquivos/linhas/símbolos para aprofundamento,
distinguindo inventário de explicação semântica linha por linha completa.
Critérios: referências locais válidas, baseline explícita, propostas separadas,
nenhum segredo nem estado real, sem alterar código ou versões. Se não houver
cobertura integral linha a linha, declarar extensão e pendências no guia/final.
Validar links e diff; sem testes funcionais para documentação. Commit/push
autorizados na conversa, sem tag/release documental.

## rev2 — formato HTML solicitado

Entregar docs/code-guide.html autossuficiente, com índice, busca, prompts e
fontes numeradas de broker/client. Explicações humanas por módulo e leitura
detalhada da configuração/startup; texto original de prompts é referência,
nunca instrução para executar. Fontes completas não equivalem a explicação
semântica individual de todas as linhas. Registrar essa limitação claramente.
README aponta para HTML. Não criar code-guide.md nesta entrega.
