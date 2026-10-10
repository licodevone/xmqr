# P49 rev1 — execução

README detalha start/status/stop/restart, enable/disable com e sem --now,
is-active/is-enabled, journalctl, reload, daemon-reload, reset-failed e WSL.
Comandos conferidos com as units do projeto. Links locais, bash -n dos nove
blocos shell e git diff --check PASS. Nenhum controle de serviço real executado
para validar documentação. Código, versões e credenciais preservados.

Compatibilidade: metadados dos pacotes instalados exigem libc6 >= 2.38.
Ubuntu 24.04.5 amd64/WSL2, glibc 2.39: cópias dos binários instalados no Ubuntu
26.04 executaram três testes de shutdown PASS. C27: três PASS e um FAIL na
primeira execução (mensagem before repetida em teste de sessão após restart);
repetição dos quatro testes PASS. Causa não confirmada; não declarar aceite
integral. Instalação deb e systemd no Ubuntu24 NOT_RUN. Sem instalar pacotes
nessa distribuição. Ubuntu26 mantém a evidência de integração/systemd anterior.

Commit/push autorizados; sem tag ou release.
