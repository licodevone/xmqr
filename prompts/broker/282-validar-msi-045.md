# P282 v1.0 · Validar o MSI do Broker 0.45.0

Entrada: candidato P281 gerado de `e8712bfcf885e3b12ce59173e1a483f5de58b5b5`, MSI 0.45.0 com SHA-256 `8f36f86db1855daf0fdf1fe043260e40413621d3bfc3cdcc9f6c00ecd2a9b99d` e baseline MSI 0.43.0 de P246 com SHA-256 `169456d2eea727c13a091eb4b268f631ac8698351dc3853094c7f3537f357ee3`.

Objetivo: verificar atualização, serviço e retorno à versão anterior antes de evolução funcional. Preservar o host e o conteúdo da árvore existente. Escopo: dois MSIs Windows x64, binários extraídos, configuração e estado sintéticos em pasta temporária e registro de evidências.

1. Conferir manifestos, hashes, propriedades ProductCode, UpgradeCode e ProductVersion e sequência de atualização. Extrair os binários sem registro de produtos ou serviços e conferir os hashes dos executáveis.
2. Em loopback, sem SCM, gerar estado sintético v16 em 0.43.0 e copiar configuração e estado com o processo parado. Exercitar MQTT 3.1.1/QoS 1 no candidato com a cópia. Induzir falha com uma configuração inválida e iniciar 0.43.0 sobre um destino novo criado do backup. Confirmar mensagem retida e entrega offline nos dois caminhos.
3. Em VM Windows x64 descartável e elevada, instalar 0.43.0, provisionar configuração isolada, verificar início/parada do serviço e MQTT, atualizar para 0.45.0 e confirmar versão registrada e preservação dos dados. Simular falha de início e reinstalar 0.43.0 com o backup. Separadamente, induzir falha do Windows Installer depois da fase de remoção para observar se o MSI restaura o produto anterior. Se a VM estiver indisponível, registrar esses critérios como bloqueados.
4. Registrar resultados reais em `prompts/registros/P282-validar-msi-045.md`. Esta etapa valida os artefatos existentes. Nenhuma versão ou código do produto precisa ser alterado.

