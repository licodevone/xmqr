# ADR 0002 — tópicos $SYS

Status: decidido para a fase 5, 2026-10-15.

O broker não publicará métricas em `$SYS` na fase 5. O monitor HTTP opcional,
limitado a loopback, já entrega agregados de cardinalidade finita e probe do
ator/writer. Adicionar uma segunda saída MQTT agora ampliaria a superfície de
ACL e criaria escolhas de retenção, periodicidade, backpressure e vazamento de
estado operacional antes do canal administrativo A09 estar aceito.

Não há namespace `$SYS` gerado ou reservado pelo broker nesta versão. Clientes
seguem sujeitos às ACLs normais para publicar/assinar filtros com `$`; não se
deve inferir que tópicos com esse prefixo são métricas oficiais XMQR. A regra
MQTT que impede `#`/`+` na raiz de casar tópicos `$` permanece preservada.

Reconsiderar publicação `$SYS` apenas com demanda operacional concreta,
namespace e ACL próprios, política explícita de não-retained ou retenção,
frequência/custo medidos e testes contra tempestade de assinaturas/restart.
O monitor B13 deve ser avaliado por seu contrato próprio; esta decisão B14 não
substitui auditoria, métricas de A09 nem gestão administrativa.
