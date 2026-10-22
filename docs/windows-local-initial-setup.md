# Configuracao inicial local Windows - P247

O diagnostico administrativo de 21/10/2026 confirmou os tres executaveis
instalados, mas os modelos de configuracao estavam sem provisionamento:
Broker sem certificados/usuarios/ACL; Client com arguments=[]; Admin sem token.
Desinstalar/reinstalar os mesmos MSIs nao prepara esses arquivos.

Correcao P247 v1.4: a primeira execucao elevada recusou uma DACL valida
porque o Windows persistiu o sinalizador AI adicional no descriptor. A
verificacao agora compara proprietario, protecao e regras exatas de acesso,
sem comparar a representacao textual completa. As restricoes permanecem.
A pasta bootstrap criada nessa tentativa pode ser reutilizada quando suas
permissoes forem exatamente as esperadas; nao e preciso exclui-la.

Correcao P247 v1.6: a proxima tentativa administrativa avancou ate a
substituicao de client.toml, mas a chamada File.Replace recusou o backup
$null convertido para string vazia pelo PowerShell. A chamada agora usa
client.toml.replaced no staging privado, recusa backup existente e verifica
novamente o hash fixado no preflight antes da troca. Vinte testes reais com
arquivos temporarios passaram, incluindo reproducao do erro e recuperacao.
Os servicos ainda nao chegaram a ser iniciados nessa tentativa.

Mantenha as versoes instaladas e os tres servicos parados. No PowerShell 7.5+
64-bit **como administrador**, execute a partir desta copia do projeto:

```powershell
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\initialize_windows_local.ps1" -StartServices
```

O script e especifico para os caminhos padrao em Program Files/ProgramData,
conta LocalService e configuracoes-modelo inalteradas. Recusa arquivos de
credenciais existentes e diretorios de destino nao vazios. Nao e uma rotina
de reparo generico para configuracoes personalizadas ou instalacoes remotas.

Ele gera uma CA local privada, certificados distintos, senha aleatoria com
Argon2id e usuario MQTT `xmqr-local` limitado ao topico `xmqr/local/test`.
Prepara o Client como assinante persistente desse topico e cria o token do
Admin com o proprio executavel instalado. Mantem TLS mutual e loopback.
Chaves/senhas nao aparecem na saida nem neste documento. A chave da CA e a
copia de seguranca do modelo ficam privadas em ProgramData/XMQR/bootstrap.

A opcao StartServices inicia Broker, Client e Admin nessa ordem, aguardando
estado Running. O resultado sem segredos fica em target/p247-setup-result.json.
Se houver falha na inicializacao, os arquivos preparados sao preservados para
diagnostico. Nao repita o provisionamento sobre arquivos ja criados.

O painel fica em http://127.0.0.1:9080/. No primeiro acesso, crie a conta web
pelo formulario de configuracao. O codigo local solicitado esta no arquivo
privado C:\ProgramData\XMQR\admin\state\token, acessivel ao administrador.
A conta web e independente do usuario MQTT. O painel inicia como observador;
o console MQTT remoto nao e configurado por esta rotina.

O Client limita messages.ndjson a 8 MiB e para se o limite for atingido;
esta rotina nao implementa rotacao automatica. Os certificados de identidade
valem um ano e a CA dois anos; a renovacao exige administracao posterior.

Para coletar o estado apos executar (inclusive se ocorrer erro):

```powershell
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\collect_windows_installed_diagnostics.ps1"
```

Validacao desta entrega: helper Rust com cinco testes, fmt, Clippy estrito e
release passaram; 17 verificacoes criptograficas em memoria passaram;
19 testes de permissoes passaram, incluindo a captura real do operador e
negativos para acesso indevido, escrita, heranca e proprietario incorretos;
20 testes de substituicao/backup/recuperacao passaram com a funcao real;
scripts parseados e revisados. A execucao completa do
inicializador/SCM permanece pendente do operador: o token restrito da sessao
de desenvolvimento nao permite aplicar as DACLs privadas. Nenhum servico
instalado foi alterado ou iniciado pela validacao automatizada.

O helper compilado deve estar em tools/windows-password-hash/target/release/
xmqr-windows-password-hash.exe (ou bin/ no pacote portavel). Ele nao recebe
senha por argumento e nao usa o fixture de testes com sal fixo.
