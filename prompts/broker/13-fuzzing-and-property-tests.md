> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/13-fuzzing-and-property-tests.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — fuzzing e testes de propriedades

Defina propriedades do codec: nunca panic, nunca alocar além do limite, progresso ou necessidade explícita de mais bytes, decode(encode(x)) preserva semântica e bytes inválidos não são aceitos silenciosamente.

Crie fuzz targets para fixed header/remaining length, strings e properties, cada packet decoder, stream fragmentado e máquina de estados. Adicione propriedades de topic matching comparadas a uma implementação simples de referência.

Use seeds de capturas e testes normativos, limites de memória/tempo e sanitização disponível. Minimize qualquer crash e converta-o em teste de regressão antes de corrigir.
