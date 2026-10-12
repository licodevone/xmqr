# P05 didático rev1 — conectar o client ao broker TCP

Entrada:P04 íntegro. Preservar broker eprotocolonãoMQTT; manter impressãoP03
do client. Usar biblioteca padrão Read/Write eTcpStream. Conectar ao endereço
loopbackP04, enviar exatamente bytesping, reservararray4, lerread_exact e
mostrar Resposta:ping viaString::from_utf8_lossy. Propagar erros comResult/?.
Nenhuma crate externa, mudança de porta ouautenticação. Client0.2.0 didático.
Comentários explicam cadaAPI nova eidentificam [P05 - NOVO/ALTERADO], impressão
[P03 - MANTIDO]. Acrescentar README/histórico/diff/registro. Testar build/lint e
client real contra o servidorP04, inclusive a partir do ZIP extraído emWindows.
Não confundir este exercícioTCP com uma sessãoMQTT ouTLS/mTLS.
