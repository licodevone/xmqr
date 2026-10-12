# P03 didático rev1 — recorte inicial: criar dois executáveis Rust

Este documento implementa agora o primeiro recorte do prompt de bootstrap.
Não é evidência de execução passada nem substitui oP03 histórico original.
Entrada: contextoP00 definido, Rust nativo Windows disponível, projeto novo.

Crie pastas broker eclient com pacotes independentes, sem dependências externas.
Use Rust2024, versão didática0.1.0 e publish=false. Binários: broker-inicial
eclient-inicial. Cada src/main.rs tem comentário identificando P03, fnmain
eprintln! com a mensagem de identificação. Sem argumentos/listener/configuração
ou publicaçãoMQTT. O programa termina normalmente depois de imprimir.

Inclua README com código eexplicação das palavras/símbolos ecomandos PowerShell.
Cargo.lock deve ser gerado peloCargo, não escrito manualmente. Use os gates
com toolchain local e sem instalar dependências. Crie ZIP com fonte íntegra,
prompts eexplicação para extração/execução Windows. Não incluir target, estado,
credenciais ou chave privada. Verificar os arquivos extraídos por hashes e
compilar/executar fora do projeto original.

Resultado esperado: broker-inicial imprime Broker MQTT: projeto inicial em Rust.
client-inicial imprime Client MQTT: projeto inicial em Rust. Exit0 em ambos.
P00 define contexto; P03 cria esta base. Recursos mais amplos do prompt original
(runtime assíncrono, logs estruturados, configuração/parada de serviço) entram
somente em recortes posteriores autorizados eexplicados antes de usar novas APIs.
