# Client Windows - assinatura persistente P248 / C152

O preparo P247 foi concluido pelo operador: Broker, Client e Admin atingiram
Running. Broker /health e /ready responderam200; Admin /api/auth/config
respondeu200 com primeira conta ainda por configurar.

A verificacao posterior encontrou zero conexoes MQTT ativas, uma conexao
total e uma sessao persistente, sem rejeicao de autenticacao/ACL. O codigo
do Client mantinha um prazo de90segundos sem mensagens de aplicacao, mesmo
recebendo PINGRESP. Essa politica CLI tambem era aplicada ao servico.

A correcao C152 limita a excecao ao runtime Windows de servico/configuracao
privada: apos SUBACK a assinatura pode aguardar mensagens continuamente.
CLI comum conserva90s; CONNECT/SUBACK, QoS2, timeout total explicito,
reconexoes limitadas e Stop/Shutdown cooperativo permanecem.

O atualizador P248 substitui somente mqtt-client.exe no caminho padrao,
com copia de seguranca do executavel anterior. Nao prepara novas credenciais,
nao modifica os TOMLs/certificados/tokens/estado e nao reinstala os MSIs.
Ele exige PowerShell7.5+64-bit como administrador, confere registro, conta,
caminhos, hash/capacidade do candidato e observa o Client por100segundos.

No projeto local, depois de o pacote validado estar disponivel:

```powershell
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\update_windows_client_p248.ps1"
```

Na copia extraida do pacote, use o mesmo script ao lado de manifest.json e
mqtt-client.exe. O script preserva ambos os executaveis se ocorrer conflito
ou falha e informa o resultado. O binario corrigido continua na versao
0.43.0; o manifesto P248/C152 identifica o hotfix por hash e origem exatos.
Reparar com MSI antigo pode restaurar o executavel anterior.

Para o primeiro acesso ao Admin, abra http://127.0.0.1:9080/ e crie a conta
web pelo formulario. O codigo local solicitado esta no arquivo privado
C:\ProgramData\XMQR\admin\state\token, acessivel ao administrador. Esse
codigo e usado somente no formulario local, sem precisar envia-lo no chat.

Nao execute initialize_windows_local.ps1 novamente: as credenciais ja foram
preparadas. Estado SCM sustentado apos o hotfix exige execucao elevada do
operador; resultados de build/testes nao substituem essa confirmacao.

O icone Client e incorporado pelo Windows SDK durante o link nativo. O
executavel e conferido por leitura dos recursos, sem alteracoes posteriores.
O pacote inclui os prompts P248/C152, registro de validacao e SHA256SUMS.
Testes automatizados aprovados nao substituem os 100 segundos de observacao
no servico instalado. Inicializacao apos reiniciar Windows, atalhos, tray e
ciclo completo dos quatro instaladores nao foram revalidados por este hotfix.
