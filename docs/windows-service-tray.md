# Serviço Windows e bandeja XMQR - P239

Implementação experimental em andamento, sem release ou instalação no computador
do operador. A fase 9 continua aberta. Veja os resultados efetivamente executados
no [registro P239](../prompts/registros/P239-windows-services-tray.md).

## Experiência da bandeja

O novo [XMQR Manager](../tools/windows-manager/README.md) é um programa Rust
independente, `xmqr-manager.exe`. A instalação coordenada inclui o gerenciador
e somente os componentes escolhidos. Cada componente instalado registra seu
próprio menu; o gerenciador consulta esse inventário periodicamente. Ausência de
um componente não cria entrada desabilitada nem mensagem anunciando sua ausência.
Sem nenhum componente, não há ícone; o processo acompanha futuras instalações.

O menu do broker oferece iniciar, parar, reiniciar, abrir o arquivo de
configuração, abrir sua pasta, abrir certificados e abrir logs. Os caminhos
vêm do registro protegido criado pelo instalador. O primeiro MSI restringe os
dados à pasta dedicada do produto; o gerenciador não lê certificados/chaves nem altera
permissões. Abrir configuração não reinicia o serviço automaticamente.

| Estado agregado | Ícone |
| --- | --- |
| Todos os serviços consultados em execução | Verde |
| Todos parados, sem falha reportada | Cinza/apagado |
| Estados mistos ou transição | Amarelo |
| Erro, falha de consulta ou estado desconhecido | Vermelho |

Cada item possui texto de estado. Verde confirma **execução segundo o Windows**,
não prontidão MQTT, conexão autenticada ou entrega de mensagens. O cliente CLI
instalado sem serviço tem atalhos, sem comandos de serviço. Erro de acesso não
é tratado como inexistência. Sair da bandeja não para os sistemas. Ações são
serializadas, com prazo, sem travar a interface. Reiniciar aguarda a parada
antes de iniciar e não força encerramento. Elevação é limitada à ação solicitada.

## Adaptador do broker

O build experimental aceita:

```text
mqtt-broker --windows-service xmqr-broker ABSOLUTE_LOG_DIR --config ABSOLUTE_CONFIG_PATH
```

Esse comando é a linha registrada pelo instalador no SCM, não um comando para
executar o serviço diretamente em um terminal. O arquivo TOML explícito usa a
mesma validação/configuração do broker e resolve caminhos relativos a partir de
sua pasta. Variáveis `MQTT_*` do ambiente não sobrepõem esse arquivo no modo de
serviço, evitando divergência entre o atalho e a configuração efetiva.

O adaptador publica Starting/Running/Stopping/Stopped. O broker só publica
Running após inicializar armazenamento e listeners. STOP/SHUTDOWN sinalizam o
mesmo encerramento cooperativo que fecha listeners, drena conexões e finaliza
o ator durável. Falha de execução é reportada ao SCM com código não zero.

`logs/service.log` contém somente eventos de ciclo de vida e categorias fixas
de erro, com uma cópia rotacionada após 1 MiB. Não contém payloads, credenciais
ou conteúdo de configuração. Os logs normais de tracing ainda usam a saída
padrão: redirecionamento operacional completo não foi homologado nesta fatia.
O tempo de desligamento real do Windows e os checkpoints de inicialização
precisam de testes de boot/shutdown em VM; não se infere garantia pelo callback.

## Builds separados e compatibilidade

Os manifests e locks da raiz continuam usados para as CLIs normais. O adaptador
é compilado apenas pelo manifest independente
[packaging/windows-service/Cargo.toml](../packaging/windows-service/Cargo.toml),
que reutiliza as mesmas fontes com a feature `windows-service-runtime`.
Não foi criado um Cargo workspace nem uma dependência entre client e broker.
O manifest separado deve acompanhar versões/dependências do manifest raiz.

O build comum não oferece a entrada de serviço. O empacotador exige o marcador
JSON `--windows-service-capabilities` do executável experimental e não substitui
o binário novo por um `.exe` antigo. Veja
[build, MSI, configuração e instalação](../packaging/windows/README.md).

## Bloqueios que permanecem explícitos

- Dependência e compilação comprovadas em 2026-10-21: `windows-service 0.8.1`,
  locks reais dos três produtos, builds debug Windows x64 MSVC, markers dos
  executáveis e 21 testes dirigidos passaram. Veja a
  [evidência P239](results/p239-windows-service-proof-20261021.json).
  Clippy estrito passa no cliente; broker/admin ainda falham nos avisos Windows
  preexistentes. Os builds comprovados não são novos MSIs nem aceite SCM.
- O armazenamento do broker continua recusando `sync_directory` no Windows.
  Um serviço com esse broker falhará ao inicializar estado novo; não é um broker
  Windows operacional aceito. Adaptar persistência NTFS e provar recuperação
  é pré-requisito, sem retirar a proteção Unix por conveniência.
- O admin ainda depende de política Unix para tokens/usuários privados.
  Seu adaptador não homologa o painel nativo; o pin do core permanece intacto.
- O client mantém restrições de credenciais/estado. Seu adaptador recusa entrada
  interativa e assinatura sem destino Windows seguro, em vez de descartar
  mensagens na saída invisível do serviço. Bridge durável continua Linux.
- Instalação elevada, UAC, ACL efetiva, login, atualização, remoção e controle
  real dos serviços ainda exigem VM descartável. Compilar WiX com fixtures
  verifica o schema do instalador, não essas propriedades.

Não houve alteração de protocolo MQTT, formato de estado, versões, tags ou
publicação. A implementação de infraestrutura não encerra W2/W3/W4/W5/W6 do
[plano Windows](windows-native-evolution-plan.md).

## Reproduzir a comprovação sem instalar serviços

Na raiz do broker, com os três repositórios vizinhos e os locks experimentais:

```powershell
python scripts/verify_windows_service_builds.py --output target/p239-proof-novo --offline
```

O diretório de evidência precisa ser novo. O runner compila as fontes atuais,
registra hashes, executa testes com pelo menos um caso selecionado e captura
saídas de fmt/Clippy e negativos reais. A saída global permanece não zero se
qualquer gate falhar, mesmo com os três builds aprovados. O relatório distingue
`builds_and_markers_pass`, `all_executed_checks_pass` e `native_acceptance`.
Os negativos fora do SCM e de plataforma não instalam nem iniciam serviços.
Use o cache padrão do Cargo ou um caminho curto: o cache profundo dentro deste
repositório causou falha de include no compilador C do AWS-LC; o mesmo lock
compilou com o cache padrão. O MSRV declarado não foi testado por esta execução
com Rust 1.99.1.
