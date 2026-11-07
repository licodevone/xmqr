# Diagnóstico do XMQR Manager

O comando `xmqr-manager --diagnose` lista os componentes e o estado observado
pelo SCM no Windows ou pelo systemd no Ubuntu. A fonte P266 acrescenta
`next_step` a cada componente, com uma orientação para aquele estado.

| Estado | Verificação indicada |
| --- | --- |
| Em execução | Checar a prontidão ou executar um teste MQTT autorizado |
| Falha | Consultar o supervisor e verificar o acesso da conta de serviço à configuração |
| Parado ou nunca iniciado | Conferir se o serviço deveria estar ativo e revisar sua configuração |
| Em transição | Aguardar e consultar o estado novamente |
| Indisponível | Conferir o supervisor e o registro do executável |
| CLI sem serviço | Rodar a CLI manualmente ou conferir o cadastro do serviço |

O diagnóstico consulta inventário e estado. A investigação sugerida é exibida
no JSON. O campo é aditivo e dispensa mudanças nos consumidores dos campos
anteriores.
