# P267 v1.1 — limitar a leitura de material TLS no broker

Entrada: Broker 0.43.0, `d561321` em `codex/p265-p266-xmqr-operacao`.
O P265 tem testes dirigidos aprovados e aceite completo pendente. A fase 9
continua aberta. As alterações locais de outros trabalhos são preservadas.

Objetivo: rejeitar antes da análise PEM arquivos de configuração TLS especiais
ou acima do orçamento. Reusar certificados CA já decodificados durante a
verificação de múltiplas CRLs.

Escopo: `src/transport/mod.rs`, módulo interno `src/transport/pem.rs`,
testes de limites e `docs/security/secure-transport.md`. Startup,
`--check-config` e rotação passam pelos mesmos loaders.

Contrato: até 1 MiB para cada arquivo de cadeia, chave ou CAs, e 8 MiB
para o arquivo de CRLs. Recusar alvos não regulares, seguir symlinks para
arquivos regulares usados na renovação, verificar metadados do handle aberto
e limitar a leitura real a teto + 1. Em Linux, abrir em modo não bloqueante
antes de verificar o handle para evitar aguardar FIFO em corrida de troca.
Zerar o buffer temporário de PEM em memória ao descartá-lo. Manter
validação de chave, validade, emissor, assinatura e revogação.

Compatibilidade: sem mudança de wire, ACL, versão, persistência ou estado.
Arquivos acima do teto passam a ser recusados. Uma falha de rotação preserva
a geração anterior conforme P100. Revisar tamanhos antes de atualizar.

Aceite: teste inclusivo N/N+1, recusa de diretório, erro redigido no
`--check-config` e regressões dos validadores aplicáveis. Usar apenas
fixtures temporárias. Executar fmt, testes e Clippy com Cargo.lock, registrar
separadamente gates Linux ou de interoperabilidade indisponíveis. Tratar
decodificação única de CA como redução de trabalho, sem alegar ganho de
throughput MQTT sem benchmark. Tag de versão após aceite do commit exato.

Revisão 1.1: corrigir os lints da nova conversão de erro e da asserção de
saída vazia. OpenSSL do Git não iniciou no sandbox. Gerar os materiais
sintéticos com o runtime criptográfico local para testar o mesmo contrato.
