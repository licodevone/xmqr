# Série didática cumulativa — Rust nativo Windows

Cada etapa é uma pasta completa e independente. Ela contém o projeto anterior
mais as alterações daquele prompt. Uma pasta já exportada fica preservada;
o próximo prompt trabalha em uma cópia, com diff que mostra as mudanças.

| Etapa | Pasta-fonte | O que foi acrescentado | Estado |
| --- | --- | --- | --- |
| P00 | projeto-inicial/prompts/00-contexto.md | Objetivo e preparação do ambiente | Documento de preparação |
| P03 | projeto-inicial | Dois executáveis iniciais, sem rede | Implementado |
| P04 | etapas/P04 | Broker de eco TCP em loopback; client P03 mantido | Implementado |
| P05 | etapas/P05 | Client TCP, envio ping e leitura da resposta; broker P04 mantido | Implementado |

P03 nesta série é uma nova implementação de recorte do prompt de bootstrap,
não uma recuperação comprovada do código original. Os snapshots históricos
e os desta série têm índices separados para não confundir essas duas origens.

Comentários no código usam `[Pxx - NOVO]`, `[Pxx - ALTERADO]` e
`[Pxx - MANTIDO]`. Eles explicam imports, funções, parâmetros e símbolos no
ponto de uso. README detalha os termos antes da digitação; cada ZIP inclui
diff contra a etapa anterior e todos os prompts já executados dessa sequência.
Não copiamos target, credenciais ou estado do serviço para os pacotes.

## Executar P05 no Windows

Na primeira janela PowerShell:

```powershell
Set-Location 'D:\projects\my-project\rapidez-projects\rapidez-broker-client\xmqr\curso\etapas\P05'
cargo run --locked --offline --manifest-path .\broker\Cargo.toml
```

Na segunda janela, na mesma pasta:

```powershell
cargo run --locked --offline --manifest-path .\client\Cargo.toml
```

O client imprime a identificação preservada e `Resposta: ping`.
O broker continua esperando; Ctrl+C encerra essa instância de estudo.
O código foi validado com a instalação nativa Windows Rust1.98.1/MSVC.
Sem Cargo no PATH ou toolchain completa, confira sua instalação antes de
alterar o código. Não é necessário WSL, Docker ou configuração do firewall.

## Próximas partes — roteiro, sem código executado ainda

1. Limites, erros, timeouts e encerramento coordenado do transporte.
2. Leitura de pacotes: cabeçalho e Remaining Length MQTT, com testes de fragmentação.
3. CONNECT/CONNACK e identificação da sessão MQTT3.1.1.
4. Assinatura e publicação QoS0, filtros e roteamento.
5. QoS1 e seus identificadores/confirmações, com retransmissão explícita.
6. Sessões, retained e estado offline, com limites.
7. Persistência, recuperação e responsabilidade durável antes de ACK.
8. QoS2 e Last Will, com transições e testes de falha.
9. TLS/mTLS, autenticação e autorização, explicadas antes de entrar no código.
10. Observabilidade, configuração, operação e distribuição.

Os números acima são partes planejadas, não IDs de prompts executados.
Cada parte terá seu próprio prompt aprovado pelo pedido, explicação dos novos
recursos, implementação, validação e ZIP acumulado. MQTT5 e WebSocket serão
etapas posteriores explícitas. P04/P05 ainda são TCP de estudo, sem MQTT.
