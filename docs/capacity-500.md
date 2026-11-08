# Capacidade de um nó com o ecossistema XMQR

O P274 amplia a configuração de um nó para até 1.000 conexões MQTT e
até 1.000 sessões. O ensaio P272 separa as conexões do broker, a carga
de mensagens e o acesso operacional aos outros componentes.

| Componente | Como usa a capacidade |
| --- | --- |
| Broker | Uma quota de conexões compartilhada pelos listeners e outra para sessões, inclusive as persistentes desconectadas. |
| Client | Uma conexão por execução de publicação ou assinatura. Várias mensagens podem usar a mesma conexão. |
| Bridge | Cada rota usa uma conexão em cada ponta. A ponta no nó consome uma vaga. |
| Admin | A visão geral consulta o monitor por HTTP, fora da quota MQTT. O console abre conexões MQTT via Client. O painel limita 16 requisições em processamento, 32 conexões HTTP e 64 sessões de login quando a autenticação por usuário está habilitada. |
| Manager Windows e Ubuntu | Inventaria e consulta serviços locais via SCM ou systemd. O inventário de até 64 componentes é independente do número de dispositivos MQTT. |

Para manter o console utilizável, deixe vagas para sua assinatura e para
a publicação enquanto ambos estiverem ativos. Exemplo com 1.000 vagas
e console usando duas conexões simultâneas, sem bridge: 998 ficam para
dispositivos. Uma bridge, observador MQTT ou serviço Client ativo também
entra na conta. Verifique a quota de sessões se houver dispositivos offline.

## Aceite em Ubuntu

Compile os binários Linux das fontes sob teste e escolha um diretório
nativo gravável para o estado temporário. O ensaio exige Python 3.11+,
permissão de loopback e descritores disponíveis para os sockets e arquivos.
Confira o limite do processo que executa o broker e do gerador com
`ulimit -n`. No laboratório de 1.000 conexões, use uma folga sobre os
1.000 sockets, por exemplo 2.048 descritores. Use os binários por caminho explícito.

```sh
python3 -B scripts/verify_suite_500.py \
  --broker /caminho/mqtt-broker --client /caminho/mqtt-client \
  --admin /caminho/xmqr-admin --state-root /caminho/laboratorio \
  --connections 1000
```

O ensaio usa 999 conexões wire e uma conexão do Client nesse perfil,
confirma o contador autenticado do Admin e envia uma publicação QoS 1
com o nó saturado. Também verifica a recusa da conexão excedente e a
reutilização da vaga. `--connections 500` mantém o cenário original e
é o padrão do script. A saída JSON identifica os binários por versão e SHA-256.

Para os Managers, execute as [fixtures Ubuntu](../tools/linux-manager/README.md)
e [os testes Windows](../tools/windows-manager/README.md). O teste com
SCM/systemd real deve rodar em instalação descartável, consultando o estado
do serviço durante o ensaio e sem reiniciar o broker.

## Medição de publicações

1.000 dispositivos com uma publicação a cada 10 s oferecem em média
100 publicações/s. Uma rajada pode entregar as 1.000 juntas. Para estimar
o máximo sustentado, eleve a taxa gradualmente com conexões fixas e
registre publicações aceitas, entregas, p95/p99, perdas, RAM, CPU e filas.
Faça a medição com QoS, TLS/mTLS, fan-out e armazenamento equivalentes ao
uso real. O ensaio de ocupação do P272 complementa o
[plano de medição P270](../prompts/broker/270-performance-baseline-044.md).
