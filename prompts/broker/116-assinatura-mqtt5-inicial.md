# P116 rev1 — assinatura MQTT 5 inicial

Data: 2026-10-16. Entrada: `main` em `502f7b1`, broker 0.15.0, P115 aceito e CI aprovada. Continuação da fase 6A antes de versão/tag.

## Objetivo e escopo

Aceitar SUBSCRIBE MQTT 5 em sessão Clean Start=1 para um ou mais filtros, QoS máximo 0/1, propriedades vazias e opções padrão (No Local=0, Retain As Published=0, Retain Handling=0). Responder SUBACK MQTT 5 com um reason code por filtro; usar 0x80 para falha de ACL/quota. Entregar PUBLISH MQTT 5 sem propriedades para mensagens vivas e retained, QoS0/1; processar PUBACK 5 de sucesso. Preservar interop cruzada com publisher MQTT 3.1.1 ou 5.

Arquivos: `src/mqtt/{codec,mod}.rs`, testes de wire/integração, `scripts/verify_interop.py`, `docs/conformance/mqtt5-status.md`, plano, changelog e registro P116. Sem migração de estado; sessão MQTT 5 continua não durável.

## Limites e aceite

Rejeitar propriedades SUBSCRIBE não vazias, opções estendidas e QoS2, packet ID zero e payload vazio antes de mutar assinatura. Não anunciar suporte MQTT 5 geral; UNSUBSCRIBE, propriedades, sessão persistente e QoS2 permanecem pendentes. Preservar ACL, quotas, limite de 64 KiB, ordem SUBACK antes de retained, MQTT 3.1.1 e segurança de transporte. Testar vetores wire positivos/negativos, assinatura real, retained, QoS1/PUBACK, cliente externo Mosquitto v5 e regressão v3.1.1. Gates: fmt, test, Clippy, build, CI. Aceite e tag somente após registro real.

Norma: <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>, §§3.8–3.9 e 3.3.

Rev2: o primeiro teste de negativos detectou que o decoder ainda aceitava QoS2 em SUBSCRIBE MQTT 5, herdado do parser 3.1.1. Recusar essa opção explicitamente antes da chamada ao roteador e repetir a suíte.
