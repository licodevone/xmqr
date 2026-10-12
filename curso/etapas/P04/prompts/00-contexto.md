# P00 — contexto da série didática

Curso: Da lógica ao Broker e Clientes MQTT utilizando Rust.
Esta série começa agora; não reconstrói a história original por suposição.

Antes de criar código, definimos o resultado: dois programas independentes,
um futuro broker e um futuro client. Rust instalado no Windows, Cargo e
editor de texto são suficientes para esta etapa. Ambiente verificado em
2026-10-12: Rust1.98.1/x86_64-pc-windows-msvc.

Contexto é a situação antes da tarefa: ferramentas, arquivos, objetivo e
limites. Não é entrada de dados do programa. Neste ponto não temos listener,
sessões, tópicos ou protocoloMQTT. P00 prepara o trabalho; o código é criado
no recorte inicialP03, conforme o próximo documento.

Fronteira: broker atenderá mensagens e conexões; client enviará/receberá;
aplicação consumidora interpretará os dados. Nesta primeira entrega apenas
criamos a estrutura e comprovamos compilação/execução, sem implementar rede.
