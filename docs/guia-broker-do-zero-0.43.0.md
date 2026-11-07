# Construindo o broker MQTT XMQR: do zero à versão 0.43.0

Edição do roteiro: 1.0, 30/10/2026. Preparado pelo P259.

Este é um percurso de construção e estudo com objetivos, arquivos de referência,
comandos e critérios de saída. O primeiro checkpoint contém código completo.
Os incrementos seguintes apontam para a implementação integral e os prompts
do projeto: não são uma transcrição, linha por linha, de todo o código Rust.
Produzir o roteiro não significa que um segundo broker foi implementado ou que
seus testes passaram. A conclusão exige executar os critérios de cada incremento.

## 1. Definir o destino e preservar o ponto de partida

O destino verificável é a tag `v0.43.0` do repositório `licodevone/xmqr`,
resolvida localmente para `db472bc64558bf0e376a902b7780a259247c5149`.
A pasta atual `xmqr/` contém commits posteriores com o mesmo número no manifesto.
Por isso, ler somente `version = "0.43.0"` não identifica a fonte publicada.

Use dois diretórios separados durante o aprendizado:

| Diretório sugerido | Finalidade |
| --- | --- |
| `xmqr-broker/` | Construção manual, começando vazio |
| `xmqr-referencia-043/` | Consulta da implementação exata da tag |
| `xmqr/`, já existente | Trabalho original, preservado |

Os nomes têm papéis diferentes: XMQR é o produto; `mqtt-broker` é o pacote e
o executável da versão publicada; `mqtt_broker` é o nome da biblioteca nos
imports Rust. A pasta pode chamar-se `xmqr-broker` sem alterar esses nomes.

O escopo final inclui o broker e o `mqtt-admin` legado. `xmqr-client` e o
admin independente `xmqr-admin` têm repositórios e versões próprios.
Gateway, dashboard de negócio e firmware de sensores ficam fora do núcleo.

Consulte a [nota 0.43.0](releases/0.43.0.md), o [aceite da fase 6](phase6-acceptance.md)
e o [registro P228](../prompts/registros/P228-release-0.43.0-state-v16.md).
A sequência abaixo é uma ordem didática proposta; não afirma recuperar
cada edição original feita antes do histórico preservado.

## 2. Preparar Windows e Linux/WSL

No PowerShell do VS Code:

```powershell
rustc --version
cargo --version
git --version
python --version
```

O manifesto da tag usa Rust 2024 e declara `rust-version = "1.88"`.
Isso expressa o mínimo declarado, não uma nova homologação de toda a árvore
com Rust 1.88 exato. O registro P228 relata gates com Rust 1.99/Ubuntu 26.04.
Na elaboração deste guia, foram observados Rust/Cargo 1.99.1 e Python 3.13.15
no Windows. Não altere ferramentas globais apenas para acompanhar as aulas.

Se faltarem ferramentas, prepare Rust pelo [instalador oficial](https://www.rust-lang.org/tools/install).
No alvo Windows MSVC, prepare também o toolchain C++/SDK exigido pelo compilador;
a disponibilidade do comando `cargo` sozinha não prova a disponibilidade do linker.

Para aceites Unix, use Ubuntu/WSL. Confira dentro dele:

```bash
rustc --version
cargo --version
python3 --version
git --version
command -v cc cmake perl pkg-config openssl mosquitto_pub mosquitto_sub
```

As compilações TLS podem exigir compilador nativo, CMake e Perl pelas dependências
criptográficas fixadas. As campanhas externas precisam dos clientes Mosquitto,
OpenSSL e Paho. A referência histórica usou Mosquitto 2.0.22, Paho 2.1.0 e
OpenSSL 3.5.5. Uma versão diferente exige novo registro de proveniência.

Mantenha estado privado e testes de recuperação no filesystem Linux nativo
do WSL, por exemplo sob `$HOME` ou `/var/tmp`, com permissões apropriadas.
Não trate uma compilação Windows ou um teste sobre `/mnt/d` como prova de
durabilidade e permissões Unix. Prerrequisito ausente deve resultar em BLOCKED.

## 3. Obter a referência sem mudar o repositório original

No PowerShell, no diretório agregador:

```powershell
Set-Location 'D:\projects\my-project\acmebr-projects\xmqr.acmebr'
if (Test-Path -LiteralPath '.\xmqr-referencia-043') {
    throw 'O destino de referência já existe; escolha um diretório novo.'
}
git clone --no-hardlinks --no-checkout .\xmqr .\xmqr-referencia-043
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar a cópia de referência.' }
git -C .\xmqr-referencia-043 checkout --detach db472bc64558bf0e376a902b7780a259247c5149
if ($LASTEXITCODE -ne 0) { throw 'Falha ao selecionar a fonte 0.43.0.' }
git -C .\xmqr-referencia-043 rev-parse HEAD
git -C .\xmqr-referencia-043 status --short
```

O primeiro resultado deve ser o SHA completo acima, e o status deve estar vazio.
O clone local copia o histórico Git, não as alterações não commitadas do original.
O checkout destacado é uma referência congelada para consulta.

Todos os links relativos deste guia abrem a cópia atual dos documentos.
Para comprovar como um arquivo era em 0.43.0, abra o mesmo caminho na referência
congelada ou use `git show v0.43.0:caminho/do/arquivo` dentro de `xmqr/`.

## 4. Criar o projeto vazio

No mesmo diretório agregador:

```powershell
if (Test-Path -LiteralPath '.\xmqr-broker') {
    throw 'O destino didático já existe; preserve seu conteúdo.'
}
cargo new xmqr-broker --bin --name mqtt-broker --edition 2024 --vcs none
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o projeto didático.' }
Set-Location .\xmqr-broker
cargo run
```

Você terá `Cargo.toml` e `src/main.rs`. O programa inicial imprime uma mensagem.
O Cargo cria um pacote executável; `--name` mantém o nome usado pelo código final
e `--vcs none` deixa a gestão Git para uma etapa explícita do seu trabalho.

Mantenha a versão didática inicial do Cargo. O número `0.43.0` só entra no
fechamento de um candidato compatível, depois de validar o escopo.

## 5. Primeiro checkpoint: listener TCP assíncrono

Acrescente em `[package]` a linha `rust-version = "1.88"`. Em `[dependencies]`:

```toml
tokio = { version = "=1.53.1", features = ["macros", "net", "rt-multi-thread", "signal"] }
```

A versão exata neste exercício acompanha a dependência direta observada na tag.
O `Cargo.lock` fixará também as dependências transitivas. No código final, preserve
o manifesto e o lock da referência para reproduzir seu grafo completo.

Substitua somente o `src/main.rs` do projeto didático por:

```rust
use std::io;
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:18883").await?;
    println!("XMQR: listener didático em 127.0.0.1:18883");

    loop {
        tokio::select! {
            connection = listener.accept() => {
                let (socket, _) = connection?;
                drop(socket);
            }
            result = tokio::signal::ctrl_c() => {
                result?;
                break;
            }
        }
    }
    Ok(())
}
```

`TcpListener` escuta conexões; `.await` permite suspender a tarefa enquanto
o evento não chega; `?` propaga erros; `select!` aguarda conexão ou Ctrl+C.
O socket é fechado imediatamente. Ainda não há interpretação de MQTT.
A porta 18883 reduz colisões com o broker já instalado na porta habitual.

```powershell
cargo generate-lockfile
cargo fmt --all -- --check
cargo check --locked
cargo run --locked
```

Em outro PowerShell, execute `Test-NetConnection 127.0.0.1 -Port 18883`.
Aceite: a conexão TCP é estabelecida, o processo continua aceitando conexões
e Ctrl+C encerra o listener. Um cliente MQTT ainda não obterá CONNACK.

## 6. Adotar o ciclo de trabalho por incremento

Antes de cada incremento, crie um prompt versionado no projeto didático e
registre o resultado real. Use IDs didáticos próprios, por exemplo `D01`,
sem reclassificar os antigos Pxx como novos trabalhos concluídos.

```text
ID/versão: Dxx v1.0
Entrada: commit, arquivos, último aceite e alterações locais.
Objetivo: comportamento observável que esta etapa acrescenta.
Escopo/arquivos: módulos envolvidos e testes correspondentes.
Requisitos: pacote MQTT, limites, estados e cláusulas OASIS aplicáveis.
Invariantes: filas limitadas, gerações, ACL e durabilidade antes dos ACKs.
Compatibilidade/migração: wire, configuração, documento/WAL e rollback.
Aceite: cenários positivos, negativos e integração necessários.
Validação: comandos, ambiente e resultados esperados.
Registro: PASS/FAIL/BLOCKED/NOT_RUN, resultado real e limitações.
```

O [modelo existente](../prompts/broker/18-feature-iteration.md) e o
[modelo de registro](../prompts/registros/TEMPLATE.md) dão a estrutura completa.
Após uma falha, atualize o prompt com a evidência e a correção pretendida antes
de alterar a implementação. Não prossiga para o incremento dependente com
critérios ainda falhos ou bloqueados.

## 7. Preparar as fronteiras dos módulos

Evolua do único `main.rs` para uma biblioteca reutilizada pelos binários.
Crie módulos quando cada responsabilidade entrar em funcionamento. Evite
copiar um arquivo final isoladamente: ele depende de tipos e contratos dos demais.

| Arquivo da referência | Responsabilidade |
| --- | --- |
| [src/lib.rs](../src/lib.rs) | Exportar módulos da biblioteca |
| [src/main.rs](../src/main.rs) | Argumentos, configuração e composição do processo |
| [src/transport/mod.rs](../src/transport/mod.rs) | TCP/TLS/WS/WSS, admissão e encerramento |
| [src/mqtt/codec.rs](../src/mqtt/codec.rs) | Decodificar e codificar pacotes |
| [src/mqtt/mod.rs](../src/mqtt/mod.rs) | Fluxo MQTT da conexão e respostas |
| [src/mqtt/topic.rs](../src/mqtt/topic.rs) | Validar nomes, filtros e correspondência |
| [src/mqtt/router.rs](../src/mqtt/router.rs) | Sessões, roteamento, QoS e transições |
| [src/mqtt/store.rs](../src/mqtt/store.rs) | Modelo durável, validação e restauração |
| [src/mqtt/limits.rs](../src/mqtt/limits.rs) | Quotas lógicas do estado |
| [src/mqtt/clock.rs](../src/mqtt/clock.rs) | Relógio lógico e expiração |
| [src/persistence/mod.rs](../src/persistence/mod.rs) | WAL, snapshot e recuperação |
| [src/persistence/actor.rs](../src/persistence/actor.rs) | Escritor e fronteira assíncrona da persistência |
| [src/persistence/backup.rs](../src/persistence/backup.rs) | Backup verificável e restore offline |
| [src/auth/mod.rs](../src/auth/mod.rs) | Credenciais, principal e ACL |
| [src/auth/dynamic.rs](../src/auth/dynamic.rs) | Bundle dinâmico e geração de segurança |
| [src/configuration.rs](../src/configuration.rs) | Configuração tipada, defaults e precedência |
| [src/monitoring.rs](../src/monitoring.rs) | Saúde, readiness e métricas limitadas |
| [src/admin_channel.rs](../src/admin_channel.rs) | Canal administrativo local autenticado |
| [src/transport/rotation.rs](../src/transport/rotation.rs) | Validação e troca transacional de TLS |
| [src/bin/mqtt-admin/main.rs](../src/bin/mqtt-admin/main.rs) | CLI administrativa legada |

Na versão final há um pacote Cargo com módulos, não um workspace multicaixa.
Os programas client/admin independente não devem virar dependências acopladas
ao executável broker. A configuração Windows de serviço observada no HEAD
posterior não pertence à árvore da tag 0.43.0.

## 8. Construir o codec MQTT 3.1.1

Leia os prompts P04 e P22. Modele pacotes com enums/structs e erros explícitos.
Implemente cabeçalho fixo, Remaining Length, campos inteiros e strings UTF-8.
Separe quadro incompleto de quadro completo inválido. TCP pode entregar um
pacote em várias leituras ou vários pacotes na mesma leitura.

Comece com CONNECT, CONNACK, PINGREQ, PINGRESP e DISCONNECT. Adicione PUBLISH,
SUBSCRIBE/SUBACK e UNSUBSCRIBE/UNSUBACK junto das etapas seguintes. Valide
o tamanho anunciado antes de reservar memória proporcional a dados remotos.

Aceite: fragmentação e concatenação; flags inválidas; UTF-8 inválido;
comprimentos truncados; pacote acima do teto; ausência de panic por entrada remota.
Referência: `codec.rs`, P04, P22 e [matriz 3.1.1](conformance/mqtt311-status.md).

## 9. Implementar conexão, keepalive e takeover

Modele os estados aguardando CONNECT, conectado e encerrando. Proíba publicação
antes da conexão e um segundo CONNECT na mesma sessão de rede. Imponha deadline
para a primeira mensagem e interprete Keep Alive conforme a versão negociada.

Ao reutilizar Client Identifier, associe uma geração de conexão à sessão.
O encerramento atrasado da conexão antiga não pode remover a conexão nova.
Limite tarefas, filas e sockets desde essa etapa; não crie um `spawn` ilimitado.

Aceite: conexão válida; recusa de identificador inválido no recorte 3.1.1;
timeout sem CONNECT; timeout de keepalive; takeover; desconexão antiga sem
alterar a nova geração. Referências: P05, P38, P93–P95, `mqtt/mod.rs` e router.

## 10. Entregar publish/subscribe QoS 0

Guarde assinaturas por sessão. SUBACK informa o resultado de cada filtro.
Encaminhe PUBLISH aos assinantes elegíveis, com QoS efetivo compatível com
publicação e concessão de assinatura. Remova assinaturas literais por UNSUBSCRIBE.

Comece com correspondência literal e acrescente filtros no incremento seguinte.
Use uma fila de saída limitada por consumidor. Defina o comportamento quando
um assinante não lê; um cliente lento não pode bloquear todos os demais.

Aceite: dois clientes reais, entrega de payload binário intacto, ausência de
entrega a um tópico diferente e ausência de entrega após UNSUBSCRIBE.
Use o cliente independente ou clientes Mosquitto. QoS 0 não recebe PUBACK.
Referências: P06, P22, P24 e `router.rs`.

## 11. Implementar filtros, retained e sessões

Implemente `+` por nível, `#` no sufixo permitido, níveis vazios e a regra para
tópicos iniciados por `$`. Combine assinaturas sobrepostas segundo o contrato
da implementação, sem multiplicar entregas acidentalmente.

Mantenha retained separado da fila offline. Payload vazio com RETAIN remove
a mensagem retida. Uma nova assinatura recebe retained elegível. Persista
assinaturas e obrigações de sessões que devam sobreviver à conexão; não
persista sockets ou tarefas. No MQTT 3.1.1, aplique Clean Session.

Aceite: filtros válidos/inválidos; replay e remoção de retained; retomada da
sessão; limpeza por Clean Session; duplicidade de filtros; replay após restart.
Referências: P08, P27, P29, P30, P33 e [filtros](wildcard-subscriptions.md).

## 12. Criar armazenamento durável e recuperação

Antes de prometer persistência, estabeleça o contrato de commit. O roteador
prepara uma transição válida; o escritor registra e confirma a durabilidade
exigida; só então se confirma a obrigação correspondente ao cliente.

Implemente escritor exclusivo, WAL, checksums, snapshot e recuperação com
formato versionado. Diferencie uma cauda incompleta de uma falha real de leitura.
Não descarte corrupção ou erro de disco como se fossem apenas EOF.
O trabalho bloqueante de disco deve respeitar a fronteira do escritor.

Aceite: processo reiniciado recupera o estado; escritor concorrente recusado;
WAL truncado conforme o contrato; corrupção e erro de leitura explícitos;
falha de gravação sem ACK de sucesso e sem publicar estado parcial.
Referências: P25, P39, P86 e [persistência](architecture/persistence.md).

## 13. Acrescentar QoS 1 e QoS 2

Para QoS 1, controle Packet Identifier, PUBACK, retransmissão e DUP nos dois
sentidos. Para QoS 2, implemente PUBLISH/PUBREC/PUBREL/PUBCOMP com estados
duráveis que sobrevivam ao restart. Não use apenas um booleano `entregue`.

Separe as obrigações de entrada e saída. A recepção pelo broker e a entrega
a cada assinante são fluxos distintos. Reconhecimentos duplicados e reconexões
não devem liberar ou concluir a obrigação errada. Identificador reutilizado
exige cuidado adicional, aprofundado no fechamento v16.

Aceite: cada transição, duplicatas, packet ID zero, perda de conexão em cada
estágio, restart com handshakes pendentes e quota inflight cheia.
Referências: P07, P26, P28, P30, `store.rs` e `router.rs`.
O ACK MQTT não prova que uma aplicação consumidora gravou seu resultado de negócio.

## 14. Last Will, segurança e administração offline

Implemente Will validado no CONNECT, publicação por encerramento anormal e
supressão no DISCONNECT normal do contrato 3.1.1. Defina comportamento em
takeover e crash, com intenção durável quando necessária. P42 é a implementação
posterior do Will; a proposta antiga P32 não é prova de conclusão.

Adicione Argon2id, credenciais privadas, principal autenticado e ACL com recusa
por padrão. A permissão deve ser conferida na assinatura, na entrega concreta
e ao restaurar obrigações. Acrescente TLS/mTLS com verificação de cadeia,
SAN/hostname, identidade e CRL conforme a configuração.

Crie `mqtt-admin` para operações locais de usuários e estado, com escrita
atômica na plataforma suportada. Separe perfis e seus diretórios de estado.
`open-lab`, `password-lab` e `acl-lab` são laboratórios explicitamente loopback;
`secure-mtls` é o padrão seguro do projeto.

Aceite: Will anormal/normal; restart; senha errada; CA e SAN incorretos;
certificado revogado; publicação/assinatura sem permissão; restore sem ampliar
acesso; variáveis incompatíveis por perfil recusadas. Referências: P10, P23,
P34, P35, P41/P42 e [auth/ACL](security/auth-acl.md).

## 15. Monitoramento, bundle dinâmico e backup

Siga os marcos P43–P47. O monitor HTTP é opcional, limitado e loopback;
readiness deve consultar o estado relevante do ator/escritor. Use labels finitos,
sem payload ou identidade privada nas métricas.

Implemente bundle de usuários/grupos/papéis/ACL e reload atômico: um bundle
inválido não substitui a geração ativa. Faça backup offline com manifesto e
hashes e restaure em destino novo. Acrescente parada coordenada e preparação
de Docker/systemd/pacote Ubuntu, sem iniciar serviços reais por uma aula.

Aceite: monitor indisponível quando o ator falha; reload inválido conserva a
política; reload válido respeita revogação; backup alterado é recusado; restore
e restart preservam semântica MQTT; desligamento fecha escritor corretamente.
Referências: [monitor](monitoring.md), [segurança dinâmica](security/dynamic-security.md),
[Docker](docker.md) e [systemd](ubuntu-systemd.md).

## 16. Configuração e quotas: completar a fase 1

Implemente TOML `version = 1` com defaults seguros, arquivo e ambiente explícito,
nessa ordem de precedência. Caminhos relativos do TOML são resolvidos contra o
arquivo. Rejeite campo/versão desconhecidos e valores inválidos antes do listener.

Configure os limites sem aumentar os tetos da referência. P58 considera o pacote
MQTT completo, incluindo o cabeçalho. Redução incompatível com estado existente
deve ser recusada sem descarte silencioso.

| Limite da referência | Teto/default relevante |
| --- | --- |
| Conexões simultâneas | Até 64, com admissão configurável |
| Tópico/filtro | 1.024 bytes UTF-8 |
| Payload | 4.096 bytes |
| Pacote MQTT completo | 65.536 bytes |
| Sessões | Até 64 |
| Retained | Até 256 mensagens |
| Assinaturas | Até 256 por sessão |
| Offline | Até 64 por sessão |
| Inflight | Até 32 por sessão |

As unidades e aplicações devem ser conferidas em `limits.rs`, `store.rs`,
`router.rs` e `configuration.rs`; não interpretar todas as quotas como globais.
Aceite: limites inferior/superior, valor zero, pacote fragmentado excessivo,
restauração com quota incompatível, admissão e liberação de conexão.
Referências: P51–P61, [configuração](architecture/configuration.md) e
[aceite fase 1](phase1-acceptance.md). P55 pendente nos textos antigos foi
superado pelo aceite; não reutilize esse estado histórico como bloqueio atual.

## 17. Robustez e capacidade: fases 2 e 3

Meça RAM, CPU, latência de ACK, fan-out e pressão de consumidores lentos
com carga e payload definidos. Preserve contagens de entregas, timeouts e erros,
não apenas uma taxa média. Execute negativos de disco, mutações com watchdog,
matriz externa e ensaios prolongados dentro do contrato de teste.

Aceite: resultados reais em ambiente identificado; nenhum ACK indevido em falha
de disco; encerramento TLS limitado; consumidores lentos não retêm recursos
indefinidamente; dados de capacidade não extrapolados para produção.
Referências: P62/P72/P80, P86/P89–P95, [capacidade](performance-pressure.md),
[falhas de disco](storage-faults.md) e [aceite fase 3](phase3-acceptance.md).
Campanhas físicas ESP32 exigem hardware e são registradas separadamente;
ausência do hardware não equivale a PASS.

## 18. Múltiplos endpoints, rotação e canal administrativo

Na fase 4, implemente endpoints mTLS adicionais com roteador, estado e admissão
compartilhados, política estática por endpoint, TLS com senha opt-in e rotação
transacional de certificados/CA/CRL. Não anuncie reload geral do TOML:
campos restart-only continuam exigindo restart.

Na fase 5, implemente canal administrativo local autenticado, autorização por
papel, comparação de versão/hash, recibo durável, deduplicação, paginação,
consulta sem payload e operações limitadas sobre sessões/retained/segurança.
Aplique efeitos e recibo no commit pertinente. Inclua rotação/exportação de
auditoria e diagnósticos sanitizados.

Aceite: certificado novo inválido conserva a geração anterior; políticas por
endpoint; operação administrativa sem permissão recusada; replay sem repetir
efeito; disputa de versão; restart e consulta do recibo; auditoria sem segredos.
Referências: P96–P113, [fase 4](phase4-acceptance.md), [fase 5](phase5-acceptance.md)
e [canal administrativo](admin-channel.md).

O admin independente evolui no próprio repositório. Não confunda suas etapas
Axx com os grupos do plano de paridade. `$SYS` não é requisito implementado
neste núcleo; P106 documenta a decisão de observabilidade.

## 19. Introduzir MQTT 5 preservando MQTT 3.1.1

Negocie a versão no CONNECT e mantenha codecs e motivos sensíveis ao contexto.
Um único parser sem contexto de versão pode interpretar propriedades como
payload ou produzir ACK incompatível.

Implemente os incrementos seguintes nessa ordem de dependências. A coluna de
versão identifica o marco histórico, não um comando para alterar o manifesto
ao terminar uma aula.

| Marco broker | Construção necessária | Prompts principais |
| --- | --- | --- |
| 0.16.0 | CONNECT/CONNACK MQTT5, pub/sub QoS0/1 e coexistência 3.1.1 | P114–P117 |
| 0.17.0 | Recusas ACL, UNSUBSCRIBE, QoS2 e propriedades CONNECT | P119–P126; conferir P125 |
| 0.18.0 | Clean Start, Session Present e Session Expiry zero/finita/infinita | P127–P129 |
| 0.19.0 | Message Expiry, expiry no DISCONNECT e Will Delay | P130–P133 |
| 0.20.0 | Receive Maximum de saída e Maximum Packet Size | P134/P136/P137 |
| 0.21.0 | Topic Alias de entrada/saída, limitado e por conexão | P138–P140 |
| 0.22.0 | Payload Format, Content Type, Response Topic, Correlation Data, User Property | P141–P143 |
| 0.23.0 | Receive Maximum anunciado no CONNACK e fronteiras de tamanho | P144/P145 |
| 0.24.0 | Retomada QoS2 com quota cheia; Retain Handling, No Local e RAP | P146–P149 |
| 0.25.0 | Subscription Identifier, persistência e múltiplos filtros | P150/P151 |
| 0.26.0 | Shared subscriptions vivas e duráveis | P152–P155 |
| 0.27.0 | Redistribuição QoS1 compartilhada sem ACK | P156/P157 |
| 0.28.0 | Recusa de método AUTH, PLAIN em TLS e reauth de mesma identidade | P158–P161 |
| 0.29.0 | Server Keep Alive, metadados do Will e expiry iniciado na publicação | P162–P165 |
| 0.30.0 | Client Identifier atribuído pelo servidor | P166/P167 |
| 0.31.0 | Interop Paho, ACKs negativos e DISCONNECT com Will | P168–P173 |

Em cada linha, atualize codec, estado, roteador, cliente de teste e migrações
afetados. Use teste wire independente: um cliente que compartilha o mesmo erro
do servidor não é evidência suficiente. Na expiração, confira mensagens retidas,
offline e obrigações em retomada. Aliases não sobrevivem a uma conexão nova.

AUTH tem escopo explícito: PLAIN inicial apenas sobre TLS/mTLS e reautenticação
explícita da mesma identidade. Não representa suporte genérico a todos os
métodos SASL ou a desafios interativos. Leia a [ADR 0007](architecture/adr-0007-mqtt5-auth-scope.md).

Aceite por incremento: capacidades novas positivas; propriedades duplicadas,
fora de contexto e acima do limite; comportamento 3.1.1 preservado; restart
quando houver estado durável; combinação com TLS/ACL e quotas. Consulte a
[matriz de propriedades MQTT5](conformance/mqtt5-property-matrix.md).

## 20. Completar diagnósticos MQTT 5

| Marco | Trabalho | Prompts |
| --- | --- | --- |
| 0.32.0 | DISCONNECT do cliente, pacote grande, alias, Remaining Length e flags | P174–P179 |
| 0.33.0 | User Property em SUBSCRIBE/UNSUBSCRIBE e propriedades impróprias | P180–P182 |
| 0.34.0 | Motivos por contexto, IDs zero e flags PUBLISH | P183–P190/P192 |
| 0.35.0 | Segundo CONNECT, UTF-8 e campos truncados | P194–P198 |
| 0.36.0 | Estrutura CONNECT, flags de SUB/UNSUB/PUBREL e pacotes exclusivos do servidor | P199–P202 |
| 0.37.0 | Tipo reservado zero, AUTH e correção de flags de controle | P203–P206 |
| 0.38.0 | Flags do CONNECT inicial e ACKs QoS | P207–P209 |

Aceite: motivo correto na fase correta, antes de aplicar estado parcial;
resposta só quando a versão e o tamanho permitido possibilitam; ausência de
sessão/Will indevidos em CONNECT recusado. Não reutilize indiscriminadamente
um único motivo de erro. P205 corrige comportamento anterior de P178;
os testes finais devem refletir essa correção.

## 21. Construir WebSocket e WSS

| Marco | Incremento | Prompts |
| --- | --- | --- |
| 0.39.0 | WS loopback `open-lab`, caminho `/mqtt`, subprotocolo `mqtt` | P210/P211 |
| 0.40.0 | WSS mTLS local com política e quota compartilhadas com TCP | P212/P213 |
| 0.41.0 | Bind WSS remoto com opt-in separado | P214/P215 |
| 0.42.0 | Allowlist exata de Origin HTTPS em WSS mTLS | P216/P217 |

WS/WSS transporta os pacotes do mesmo broker. Não crie roteador ou banco de
sessões separado por transporte. `Origin` permitido não substitui autenticação
MQTT, certificado cliente ou ACL. O WS aberto continua restrito ao laboratório.

P218–P222 acrescentam provas de restart/crash, fragmentação, limites e navegador
real para o contrato T01. Sua posição numérica não representa mudança de versão
do pacote broker. Confira os registros ao reivindicar o aceite de transporte.
Aceite: cruzamento TCP/WSS, clientes lentos, framing inválido, quota compartilhada,
TLS/SAN, Origin incorreto e durabilidade após restart/crash.
Referência: [aceite fase 7](phase7-acceptance.md).

## 22. Fechamento 0.43.0: P227 e estado durável v16

O último incremento não é apenas mudar o número da versão. Execute o contrato
integrado da fase 6 e corrija as diferenças encontradas. Leia P227 e seus
suplementos A, C, D, E, F, G, H, I e J presentes na referência.

O fechamento cobre VBI canônico, alias válido não mapeado, fairness de shared
subscriptions, Will no takeover, progresso do controle com quota de envio zero,
fronteiras de propriedades e interoperabilidade de alias/AUTH.

P227E introduz relógio lógico com piso durável, intervalo original de expiração,
intenção conservadora de envio e identidade durável da obrigação. A distinção
entre Prepared e MayHaveSent impede que uma conclusão tardia baseada apenas
no Packet Identifier descarte uma entrega diferente após reutilização do ID.
MayHaveSent não prova que bytes chegaram ao peer.

O broker lê documentos v1–v15 e grava v16. Dados antigos não recebem intervalo
original inventado. A revisão do estado deve abranger publicação, replay,
expiração, handshakes QoS1/2 e recuperação.

Aceite: todos os grupos 6A–6D passam com fontes/binários identificados; migração
v15→v16; testes de relógio e identidade; fronteiras de metadados; testes de
pacote Ubuntu e rollback. P228/P228B documentam a distribuição final.

## 23. Conhecer as dependências do produto final

Não acrescente todas as crates na primeira aula. Introduza cada grupo quando
a responsabilidade correspondente entrar no projeto.

| Grupo no manifesto da tag | Uso |
| --- | --- |
| Tokio | Runtime, rede, canais, timers e sinais |
| Rustls, tokio-rustls, rustls-pemfile, x509-parser | TLS/mTLS, PEM e certificados |
| Argon2, rand_core, subtle, zeroize, rpassword | Credenciais e tratamento de material sensível |
| Serde, serde_json e TOML | Representação tipada de configuração/documentos |
| fs2, crc32fast e sha2 | Exclusão de escritor, integridade e hashes |
| thiserror | Erros tipados |
| tracing e tracing-subscriber | Eventos e filtragem de logs |
| async-tungstenite, ws_stream_tungstenite, futures-util | Transporte WebSocket assíncrono |
| libc, sob `cfg(target_os = "linux")` | Integrações nativas específicas |
| tempfile, em dev-dependencies | Isolamento de testes |

Para reconstruir exatamente, consulte `Cargo.toml` e `Cargo.lock` na tag.
O HEAD atual contém adaptações Windows posteriores; suas dependências não
devem ser tratadas como parte da tag. Preserve MIT e os avisos de terceiros.

## 24. Executar os gates de cada incremento

Depois de gerar o lock inicial e após cada alteração funcional:

```text
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked --bins
```

Só faça build release quando o incremento justificar ou no candidato final:

```text
cargo build --locked --release --bins -j 1
```

`--locked` exige coerência com o lock. Um novo recurso que altera dependências
precisa atualizar o lock de maneira intencional; não remova a opção para esconder
divergências. `-j 1` limita concorrência de compilação, não conexões do broker.

Adicione negativos para wire, armazenamento, autenticação e ACL. Para mudanças
entre componentes, execute integração e interoperabilidade. Registre versão
do toolchain, plataforma, código de saída, fonte e limitações. Não transforme
um teste ignorado, uma ferramenta ausente ou um resultado histórico em PASS novo.

## 25. Reproduzir a fonte final num laboratório Linux isolado

Esta seção materializa a referência executável completa sem esperar a digitação
de todos os módulos. Ela também permite comparar o comportamento do seu projeto
manual. Execute no Bash do Ubuntu/WSL, em diretório novo no filesystem Linux:

```bash
set -euo pipefail
umask 077
lab="$(mktemp -d "$HOME/xmqr-043.XXXXXX")"
printf 'Laboratório: %s\n' "$lab"
cd "$lab"

git clone https://github.com/licodevone/xmqr.git xmqr
git -C xmqr checkout --detach db472bc64558bf0e376a902b7780a259247c5149
test "$(git -C xmqr rev-parse HEAD)" = db472bc64558bf0e376a902b7780a259247c5149

git clone https://github.com/licodevone/xmqr-client.git xmqr-client
git -C xmqr-client checkout --detach 501cde2ffbae6985f033ed8be60d9ad6dd8c18c4
test "$(git -C xmqr-client rev-parse HEAD)" = 501cde2ffbae6985f033ed8be60d9ad6dd8c18c4

git clone https://github.com/licodevone/xmqr-admin.git xmqr-admin
git -C xmqr-admin checkout --detach 4483a356196db93f99340bc7aa3b3cabfc4af810
test "$(git -C xmqr-admin rev-parse HEAD)" = 4483a356196db93f99340bc7aa3b3cabfc4af810

unset CARGO_TARGET_DIR
for repo in xmqr xmqr-client xmqr-admin; do
    (
        cd "$lab/$repo"
        test -z "$(git status --porcelain)"
        cargo fmt --all -- --check
        cargo test --locked -j 1
        cargo clippy --locked --all-targets -j 1 -- -D warnings
        cargo build --locked --bins -j 1
        cargo build --locked --release --bins -j 1
        python3 scripts/license_inventory.py --check
    )
done

"$lab/xmqr/target/release/mqtt-broker" --version
"$lab/xmqr/target/release/mqtt-admin" --version
"$lab/xmqr-client/target/release/mqtt-client" --version
"$lab/xmqr-admin/target/release/xmqr-admin" --version
```

Resultados de versão esperados: broker/legado `0.43.0`, client `0.40.0`, admin
independente `0.11.0`. São os pares do aceite histórico desse broker.
O client `0.43.0` mais recente e a bridge `0.5.0` pertencem a outro marco.
Não presuma compatibilidade apenas por igualdade dos números de versão.

Mantenha o valor impresso de `$lab` para os terminais seguintes. Não copie
credenciais ou estado do serviço instalado para esse laboratório.

## 26. Fazer o primeiro pub/sub com o produto completo

Use os binários da seção anterior. Em um Bash novo, defina `lab` com o caminho
impresso, valide que ele existe e inicie o broker em primeiro plano:

```bash
lab="$HOME/SEU-DIRETORIO-XMQR-043"
test -x "$lab/xmqr/target/release/mqtt-broker"
mkdir -m 700 "$lab/estado-open-lab"
env -i PATH="$PATH" HOME="$HOME" \
    MQTT_MODE=open-lab MQTT_BIND=127.0.0.1:18883 \
    MQTT_STATE_DIR="$lab/estado-open-lab" RUST_LOG=info \
    "$lab/xmqr/target/release/mqtt-broker"
```

Se a pasta de estado já existir, pare e escolha uma pasta nova; não remova
estado para contornar uma falha. Se a porta estiver ocupada, escolha uma
porta de laboratório livre e atualize os três terminais.

Terminal assinante, substituindo o mesmo caminho:

```bash
lab="$HOME/SEU-DIRETORIO-XMQR-043"
"$lab/xmqr-client/target/release/mqtt-client" sub \
  --open-lab --host 127.0.0.1 --port 18883 \
  --client-id aula-sub --topic aula/temperatura --qos 1
```

Terminal publicador:

```bash
lab="$HOME/SEU-DIRETORIO-XMQR-043"
"$lab/xmqr-client/target/release/mqtt-client" pub \
  --open-lab --host 127.0.0.1 --port 18883 \
  --client-id aula-pub --topic aula/temperatura --qos 1 --message '25.4'
```

Aceite: o assinante recebe o tópico e o payload `25.4`, com QoS do contrato.
Encerre cada processo com Ctrl+C no respectivo terminal.
Este ensaio é MQTT de laboratório sem TLS; execute os testes TLS/ACL próprios
para reivindicar os outros perfis. Consulte o [laboratório existente](laboratorio-mqtt-aberto.md).

## 27. Executar o contrato integrado da fase 6

O executor exige os três repositórios irmãos limpos, seus binários nos `target`
locais e o cliente compilado em debug e release. Não use a árvore original
com mudanças locais. Paho, Mosquitto e OpenSSL precisam estar disponíveis;
o executor não instala dependências.

Além das três fontes finais, prepare as fontes históricas de migração usadas
pelo workflow. No mesmo Bash com `$lab` da seção 25:

```bash
cd "$lab"
git clone https://github.com/licodevone/xmqr.git legacy-broker
git -C legacy-broker checkout --detach 24d219816fdac3e47115bcb2e59edd55b0c11407
git clone https://github.com/licodevone/xmqr-client.git legacy-client
git -C legacy-client checkout --detach 235f20d097b674fadcbdf85d8c8f1c581ff1eba9
git clone https://github.com/eclipse-paho/paho.mqtt.python.git paho
git -C paho checkout --detach af64a4365c6ac5a7a4d339e7b00f44df91353b35

(
    cd "$lab/legacy-broker"
    cargo build --locked --bin mqtt-broker -j 1
)
(
    cd "$lab/legacy-client"
    cargo build --locked --bin mqtt-client -j 1
)

mkdir -m 700 "$lab/evidence"
mkdir -m 700 "$lab/evidence/native-state"
cd "$lab/xmqr"
python3 scripts/test_phase6_acceptance.py
PYTHONPATH="$lab/paho/src" python3 scripts/verify_phase6_acceptance.py \
  --legacy-broker "$lab/legacy-broker/target/debug/mqtt-broker" \
  --legacy-client "$lab/legacy-client/target/debug/mqtt-client" \
  --state-root "$lab/evidence/native-state" \
  --report "$lab/evidence/phase6.json"
```

Cada relatório deve ter um caminho novo. O executor recusa sobrescrita de
evidências. Se houver retry, use novo nome e nova pasta de estado.
Comando ausente ou fixture sem pré-requisito deve ficar BLOCKED.

O contrato histórico passou 69/69 fixtures: 32 em 6A, 13 em 6B, 12 em 6C
e 12 em 6D. Houve também 311 testes Rust do broker no aceite final, com seis
campanhas fuzz opt-in explicitamente ignoradas no gate comum. Esses são números
históricos do registro, não resultados reexecutados na criação deste guia.

| Grupo | O que precisa estar coberto |
| --- | --- |
| 6A | Negociação, codec, propriedades por contexto, motivos e coexistência |
| 6B | Sessões, expiry, Will Delay, crash e migrações reais |
| 6C | Receive Maximum, packet size, controle, aliases e metadados |
| 6D | Opções/IDs de assinatura, shared/failure/fairness e AUTH |

Confirme relatório, proveniência e hashes antes e depois, não só o marcador
impresso de sucesso. O [workflow](../.github/workflows/phase6-acceptance.yml),
o [executor](../scripts/verify_phase6_acceptance.py) e o
[aceite](phase6-acceptance.md) descrevem as condições completas.

## 28. Tratar migração e rollback antes da primeira gravação v16

Pare o broker antigo de forma coordenada e preserve backup privado do estado
v15. Verifique manifesto, hashes e versão do backup. O backup de snapshot/WAL
não inclui `.mqtt-broker-profile`; preserve separadamente seus bytes, perfil
original e permissões. A restauração deve manter o marcador coerente com o
perfil, com o broker parado, sem fabricar marcador para burlar recusa.

O broker novo grava v16. Para voltar a um leitor v15, restaure o backup anterior
em destino novo com o broker parado e use o executável apropriado.
Reinstalar o executável antigo sobre o estado v16 não faz downgrade dos dados.
Aceite: leitura v15 e migração; recusa segura de v16 pelo leitor antigo;
recusa de restore sem marcador; restauração válida e reabertura do backup15.
Siga [P228B](../prompts/registros/P228-distribution-artifacts.md) e a nota da release.

## 29. Preparar pacote, imagens e proveniência

Após os gates funcionais, prepare artefatos em ambiente descartável.
No broker congelado, `python3 scripts/build_deb.py --help` e
`python3 scripts/release_assets.py --help` apresentam os argumentos reais.
Use os procedimentos de [systemd/pacote](ubuntu-systemd.md), [Docker](docker.md)
e P228/P228B para construir e verificar o candidato, incluindo:

1. Build dos binários da fonte exata e inventário de licenças.
2. Pacote Ubuntu 26.04 amd64 e imagens com bases/alvos próprios.
3. Instalação, upgrade, restore e rollback em ambiente descartável.
4. Execução dos binários extraídos/instalados; correspondência com a fonte.
5. SHA-256, manifesto, notices e relatórios sanitizados.

O `.deb` Ubuntu e as imagens Bookworm têm caminhos de construção distintos.
Não insira o pacote Ubuntu numa base diferente presumindo compatibilidade.
Não exija que builds locais com toolchains diferentes produzam hashes iguais
aos da release; o hash deve identificar o artefato efetivamente testado.

Como a tag `v0.43.0` já existe e é imutável, use-a para reprodução. Uma nova
implementação didática precisa do próprio versionamento e das próprias
evidências. Não mova a tag existente. Este roteiro não executa publicação,
instalação de serviço ou alterações de permissões do sistema do operador.

## 30. Checklist de conclusão

- [ ] Projeto manual com módulos, limites e ownership compreendidos.
- [ ] CONNECT/pub-sub, filtros, retained, Will e QoS0/1/2 comprovados.
- [ ] Persistência e recuperação, negativos de disco e commit/ACK corretos.
- [ ] TLS/mTLS, senhas, ACL e reload com negativos comprovados.
- [ ] TOML, quotas, monitoramento e operações administrativas comprovados.
- [ ] MQTT5 completo no recorte 6A–6D, preservando MQTT3.1.1.
- [ ] WS/WSS e Origin no contrato documentado.
- [ ] Estado16, relógio/identidade, migração e rollback comprovados.
- [ ] Gates locais e integrados executados na fonte e nos binários identificados.
- [ ] Pacote e imagens testados, hashes e avisos de terceiros verificados.
- [ ] Resultados, bloqueios e limites registrados; nenhum aceite presumido.

Concluir o roteiro significa chegar ao comportamento da versão experimental
0.43.0 no contrato verificado. Não demonstra certificação MQTT5 integral,
resiliência a falha física de energia, equivalência integral a Mosquitto ou
homologação de produção. Serviços/MSI/Manager Windows de P239 em diante e a
bridge distribuída com o client têm seus próprios percursos, posteriores ou
independentes deste alvo de fonte.

## Referências normativas e de ferramentas

- [OASIS MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
- [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
- [Cargo: criação de pacotes](https://doc.rust-lang.org/cargo/commands/cargo-new.html)
- [Tokio TcpListener](https://docs.rs/tokio/1.53.1/tokio/net/struct.TcpListener.html)
- [Tokio select](https://docs.rs/tokio/1.53.1/tokio/macro.select.html)
- [Tokio ctrl_c](https://docs.rs/tokio/1.53.1/tokio/signal/fn.ctrl_c.html)

Use OASIS para requisitos normativos e vincule as cláusulas aos testes de cada
incremento. A matriz do projeto descreve o recorte e as escolhas implementadas.
Textos históricos podem conter propostas superadas; a fonte exata, o registro
posterior de execução e o aceite correspondente precisam ser confrontados.

## Apêndice A — catálogo de prompts presentes na tag v0.43.0

O catálogo abaixo é extraído de `git ls-tree` da tag. Ele é um índice de consulta,
não uma ordem de execução automática: há planos, investigações, documentação,
correções e publicações intercalados. Para a construção, use as dependências
das etapas 8–22; para uma decisão específica, leia também seu registro real.

<!-- P259:CATALOGO -->
