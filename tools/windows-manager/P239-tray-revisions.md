# P239 - revisões de execução da bandeja

## v1.1 - dependências disponíveis e backend de serviços

Antes da implementação do backend: cargo fetch falhou por DNS de crates.io no
ambiente restrito. Cache local oferece tray-icon 0.25.1, tao 0.37.1 e winreg 0.55.
Usar essas versões, MSRV 1.90 somente para o gerenciador independente; versões e
MSRV dos três produtos não mudam. Não contornar a restrição de rede.

Substituir windows-service/winit/runas/open no gerenciador por tao e consultas
locais PowerShell/.NET/CIM. Scripts fixos, dados enviados por ambiente ou
literais PowerShell escapados; nunca avaliar configuração/argumentos do usuário
como código. Serviços precisam corresponder ao inventário HKLM protegido,
com nomes limitados. Saída JSON limitada, processo com prazo e sem janela.

Controle elevado usa somente o próprio executável, ação e ID validados, após
ação explícita e uma operação por vez. Helper relê inventário e identidade do
serviço. Não ampliar permissões, não force-stop, não iniciar serviços pelo teste.
Inspeção visual/elevação/ciclo MSI pendentes de ambiente apropriado.

## v1.2 - revisão preventiva da identidade e PowerShell

Antes dos gates finais: status verde também exige que o ImagePath do SCM
corresponda ao executável instalado, não somente o nome do serviço. As consultas
retornam um booleano de identidade, sem expor argumentos. Restringir PSModulePath
ao diretório de módulos do Windows para impedir autoload de módulos do usuário
no helper elevado. Scripts e dados continuam separados.

## v1.3 - teste vazio e revisão de confiança do SystemRoot

Teste inicial: 8/9 PASS; consulta de lista vazia falhou no contrato JSON do
PowerShell 5.1. Antes de corrigir, registrar: tratar explicitamente o resultado
nulo de ConvertFrom-Json para [] e devolver array JSON vazio, sem consultar CIM.
Revisão de segurança encontrou SystemRoot herdado do ambiente como raiz de
executáveis do helper. Resolver SystemRoot no registro HKLM protegido, visão
64-bit de Windows NT/CurrentVersion, e manter PSModulePath limitado a essa raiz.
