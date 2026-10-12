# P04 didático rev1 — acrescentar comunicação TCP ao broker inicial

Entrada: snapshotP03 compilado noWindows, dois pacotes independentes.
Preservar oclientP03 e a impressão inicial dobroker. Acrescentar std::io/Read/
Write eTcpListener, sem dependências externas. Alterar assinatura main para
io::Result<()>; bind somente127.0.0.1:18830; anunciar endereço real depois do
bind; aceitar conexões sequencialmente; ler buffer512 atéEOF; devolver bytes
recebidos comwrite_all. Propagar falhas por? e retornarOk(()) quando aplicável.

Este é ecoTCP de aprendizado, não parserMQTT. Sem TLS, autenticação, timeout
ou concorrência nesta fatia; não expor listener naLAN. Explicar cada símbolo
novo e os resultados parciais de read. Validarformatação/build/lint eeco real
fragmentado emWindows. Só modificar broker/Cargo.toml, lock e main; documentos
atuais acrescentados, documentos anteriores preservados emhistorico.

Saída: mensagemP03 eTCP de estudo em127.0.0.1:18830; processo espera conexão.
Encerramento manual porCtrl+C nesta etapa. EmP04,client ainda é identificaçãoP03.
