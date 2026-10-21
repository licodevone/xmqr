# Instaladores Windows experimentais — P239

Os arquivos deste diretório implementam empacotamento nativo. Não constituem
release aceita nem prova de instalação, persistência ou segurança no Windows.
O broker ainda recusa o armazenamento durável fora de Unix e o admin ainda
recusa token privado sem a política Unix. Essas recusas foram preservadas.
O client de serviço também mantém as restrições nativas de credenciais e saída.

## Componentes independentes

- `Product.wxs`: MSI parametrizado do broker, client ou admin. Cada pacote
  registra apenas seu executável, serviço e entrada da bandeja. O serviço usa
  `NT AUTHORITY\LocalService`, início automático e parada cooperativa. O MSI
  **não inicia o serviço**, pois configuração/credenciais precisam ser preparadas
  e os gates nativos ainda estão abertos.
- `Manager.wxs`: MSI separado do gerenciador `xmqr-manager.exe`. Uma entrada
  HKLM Run inicia a bandeja no login normal do usuário. A remoção de um componente
  não remove o gerenciador dos demais. Sem componentes registrados, o gerenciador
  não mostra ícone. Sua remoção é explícita em Aplicativos do Windows.
- `install-windows.ps1`: instalação coordenada do gerenciador e dos componentes
  escolhidos. Verifica os SHA-256 antes de abrir o Windows Installer com UAC.
  Ao ser executado em sessão não elevada, abre a bandeja após instalar. Não
  encerra nem inicia os serviços. Se executado elevado, deixa a bandeja para o
  próximo login normal, evitando uma interface permanentemente privilegiada.

## Build da fonte exata

Pré-requisitos: PowerShell 7 para o build, Rust MSVC x64 e ferramentas de linkagem,
WiX 7, Python 3.11+, acesso às
dependências dos manifests. Nenhum desses pré-requisitos é instalado pelo script.
Os executáveis de serviço usam os manifests independentes
`packaging/windows-service/Cargo.toml` de cada repositório. Os binários normais
da raiz não contêm o adaptador e nunca são usados como substitutos.

Quando houver acesso à rede, resolver uma vez e revisar/versionar os lockfiles:

```powershell
cargo generate-lockfile --manifest-path packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path ../xmqr-client/packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path ../xmqr-admin/packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path tools/windows-manager/Cargo.toml
```

Depois, a partir de `xmqr/`:

```powershell
./scripts/build-windows.ps1 -Components broker,client,admin
# Para compilar e empacotar somente a bandeja:
./scripts/build-windows.ps1 -ManagerOnly
```

O build sempre usa `--locked`, recompila a fonte corrente e para se faltar
lockfile ou se houver qualquer erro. Somente depois cria um diretório novo em
`dist/windows/candidate-*`, com MSIs, manifesto, executáveis identificados por
hash, commits/estado sujo, script de instalação e `SHA256SUMS.txt`. Não usa um
`.exe` antigo já presente em `target/`. Não assina, instala, publica nem cria tag.
Cada executável de serviço precisa também responder ao probe
`--windows-service-capabilities` com JSON schema 1, componente correto e
`service_entrypoint=true`; um build convencional é recusado antes de empacotar.
O build coleta os textos LICENSE/NOTICE das dependências resolvidas no cache
Cargo e os inclui em `notices/` dentro de cada MSI e também no diretório gerado.
Ausência de texto de licença bloqueia o pacote; os avisos não são substituídos
apenas por uma tabela de nomes de licenças.
Hashes verificam integridade; não substituem assinatura/autenticidade.

## Instalação futura em VM descartável

Após resolver os bloqueios e validar os binários, a partir do pacote gerado:

```powershell
./install-windows.ps1 -Components broker
# Ou selecione somente os softwares necessários:
./install-windows.ps1 -Components broker,client,admin
# Um pacote contendo somente a bandeja pode ser instalado assim:
./install-windows.ps1 -ManagerOnly
```

Cada MSI também pode ser instalado individualmente. **O MSI do broker sozinho
não instala nem inicia a bandeja**: use o script coordenado ou instale também
o MSI do gerenciador. O MSI do gerenciador configura o próximo login; o script
coordenado também o abre ao final quando executado sem elevação permanente.
O instalador e o gerenciador são localizados pelo registro protegido HKLM 64-bit,
sem confiar em SystemRoot/ProgramFiles herdados do ambiente da sessão.

O diretório de dados fica restrito ao caminho dedicado padrão em ProgramData;
o MSI rejeita `DATADIR` diferente antes de aplicar permissões. Isso evita aplicar
uma DACL privada a uma raiz de disco ou pasta compartilhada. Caminhos de dados
personalizados ficam pendentes de validação nativa, incluindo reparse points.
O diretório padrão é lembrado em HKLM para upgrades.
O `INSTALLFOLDER` padrão é `Program Files\XMQR\Broker|Client|Admin|Manager`.
Não coloque binários/configuração em local gravável por usuários comuns.
Outro candidato da mesma versão é recusado para evitar instalações duplicadas
com ProductCodes diferentes. Remova o candidato anterior antes de reinstalar;
os dados permanecem. Reparo/manutenção do mesmo pacote continuam disponíveis.

Arquivos padrão, relativos a `ProgramData\XMQR\<componente>`:

| Componente | ID | Serviço | Configuração |
| --- | --- | --- | --- |
| Broker | `broker` | `xmqr-broker` | `broker.toml` |
| Client | `client-default` | `xmqr-client-default` | `client.toml` |
| Admin | `admin` | `xmqr-admin` | `admin.toml` |

Cada instalação cria `certificates`, `logs` e `state`. O template inicial é
preservado em upgrade e remoção (`Permanent`/`NeverOverwrite`). Não são
distribuídos certificados, chaves, senha, token nem estado. O broker usa mTLS
loopback por padrão; o client permanece deliberadamente sem argumentos até
provisionamento. O admin mantém HTTP loopback autenticado.

Dados/configuração/certificados recebem DACL protegida: SYSTEM e Administrators
com acesso total; LocalService com leitura. Logs e estado permitem escrita de
LocalService. Nenhum acesso amplo a Everyone/Users é concedido. Abrir a pasta
de certificados poderá exigir credenciais administrativas. Uma conta de serviço
compartilhada é uma limitação desta primeira fatia; isolamento por SID de serviço
e acesso de operadores precisam de validação própria antes de produção.

Ao editar caminhos internos da configuração depois da instalação, atualize também
os atalhos registrados quando aplicável; não há inferência nem leitura de chaves
privadas pelo gerenciador. `PanelUrl` do admin aponta inicialmente para
`http://127.0.0.1:9080/`; ajuste-o se provisionar outra porta loopback.

## Contrato com a bandeja

Registro **HKLM 64-bit** `SOFTWARE\XMQR\Components\<id>`:

| Valor | Conteúdo |
| --- | --- |
| Kind | `broker`, `client` ou `admin` |
| DisplayName | Nome visível do componente |
| Executable | Caminho absoluto do executável instalado |
| ServiceName | Serviço deste componente |
| ConfigFile | Arquivo real instalado no diretório dedicado do componente |
| CertificatesDir | Diretório de certificados instalado |
| LogsDir | Diretório de logs instalado |
| PanelUrl | Somente admin; URL HTTP loopback |

A desinstalação para/remove apenas o serviço e o registro do componente; conserva
dados e a localização lembrada em `SOFTWARE\XMQR\Install\<id>`. Não há remoção
recursiva de dados. A bandeja detecta a remoção sem reinstalação.

## Validação

`python scripts/verify_windows_packaging.py` verifica os contratos estáticos.
`--wix` acrescenta compilação de MSIs **de fixture** em diretório temporário,
com arquivos de teste explícitos, sem instalar ou executar nenhum software.
Isso prova schema/linkagem WiX e não um pacote de produto pronto.

Aceite operacional pendente: instalação limpa em VM elevada, conta/ACL efetiva,
boot/login, parada/reinício, remoção de cada combinação de componentes, upgrade,
reparo, rollback e preservação de dados. A fase 9 permanece aberta.
