# P266 v1.1 — orientação no diagnóstico do Manager

Entrada: broker `7c7a989`, Manager Windows 0.1.1 e Ubuntu 0.1.0.
Preservar alterações locais existentes nos READMEs e nas variantes de terminal.

Objetivo: `--diagnose` oferece orientações de investigação por estado
observado, em Windows e Ubuntu, preservando inventário e status atuais.
Separar falha reportada pelo supervisor, parada, transição, CLI sem serviço e
estado indisponível. Estado em execução indica processo, não saúde MQTT.

Escopo: Manager de desktop Windows/Ubuntu, testes e registro. A saída ganha
um campo aditivo `next_step` por componente. Nenhuma ação de controle,
elevação, leitura de segredos ou instalação é necessária para diagnóstico.

Aceite: exercício das classificações e instruções de estados; fixtures sem
SCM/systemd reais para a lógica. Fmt/test/clippy/build locked no Windows;
testes Python no Ubuntu Manager e verificação de sintaxe. Validação de
pacotes/serviços e release por plataforma após gates próprios.

Revisão 1.1: a fixture que recusava todo o systemd impedia o inventário.
Exercitar estado indisponível por divergência de executável no `show`,
mantendo o inventário e verificando que nenhum controle é solicitado.
