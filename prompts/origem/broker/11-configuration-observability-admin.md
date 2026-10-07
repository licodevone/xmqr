# Prompt — configuração, observabilidade e administração

Defina esquema de configuração versionado com defaults explícitos, validação cruzada, precedência arquivo/ambiente/CLI e mensagens com caminho do campo. Classifique campos como estáticos ou recarregáveis; reload deve ser atômico ou rejeitado.

Adicione logs estruturados correlacionados por connection/client/session sem expor dados sensíveis; métricas de conexões, pacotes, bytes, razões de desconexão, sessões, filas, inflight, persistência e latência, evitando labels de alta cardinalidade; traces somente onde agregam diagnóstico.

Crie health, readiness e administração em listener separado ou local. Inclua graceful shutdown, drenagem, dump de configuração efetiva redigida e diagnóstico de capacidade.

