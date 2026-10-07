# Sequência do XMQR existente

1. Leia contrato-base.md, broker/00-project-context.md e COBERTURA.md.
2. Para um pedido novo, prepare um ou mais prompts antes de alterar arquivos.
3. Para diagnóstico, leia código primeiro; broker/36 é o gate do snapshot atual
   somente quando execução de testes for autorizada. Não iniciar broker por esta leitura.
4. Manutenção dos perfis e CLI: broker/34, broker/35 e clients/24.
5. Validação/reconciliação atual: broker/36, broker/39 e broker/40.
6. Propostas dependentes de autorização: broker/37 (limites), broker/38 (Client ID
   e deadlines), broker/32 (Will), parcelas futuras de broker/11 (operação).
7. broker/33 descreve filtros já implementados: auditar, não aguardar Will
   nem reaplicar bootstrap. broker/09 é futuro MQTT 5.0.
8. broker/03 e broker/22–31, clients/19–23 são referências históricas de escopo;
   preservam detalhes úteis sem certificar autoria/execução. Não executar em série
   sobre o XMQR pronto. 0.2.0 em nomes de arquivos é histórico, não versão atual.
9. Gates transversais broker/10 e broker/12–17 exigem evidência; benchmarks,
   fuzzing, interop TLS/ACL e operação seguem parcialmente pendentes.

Setup deve confirmar plataforma e ambiente, nunca instalar ferramentas ou gerar
credenciais automaticamente. Rust/MSRV vem do manifest; administração atômica
exige Linux/WSL. O consumidor mantém suas próprias trilhas: nenhuma foi importada.
Uma falha ou pré-requisito ausente interrompe o gate dependente; não presumir PASS.

## Instruções, skills e agentes do XMQR

Leia [AGENTS.md](../AGENTS.md) e [uso da configuração local](../docs/agent-workflow.md).
O [prompt P-DOC-02](01-configurar-agentes-skills.md) registra a preparação desta
configuração. Skills em .agents/skills e papéis TOML em .codex/agents pertencem
ao XMQR; os materiais originais permanecem intactos. Clientes continuam no índice.


P41: [limite compartilhado de 1024 bytes](broker/41-topicos-filtros-1024.md)
e [registro de execução](registros/P41-topicos-1024.md). P37 preserva a análise
anterior; a decisão autorizada foi ampliar somente tópico/filtro.
