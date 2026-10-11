# P52 rev1 — implementação da configuração TOML

Base: main pós-P51, árvore limpa; confirmar HEAD no registro. Broker0.10.0.
Pedido autorizado: implementar a próxima etapa, prompt antes do código;
commit/push e tags/releases quando necessário, preservando tags existentes.

Objetivo: MQTT_CONFIG carrega TOML version=1, com defaults < arquivo < variáveis
MQTT_* explícitas. Não modificar ambiente global (Rust2024/unsafe proibido).
Arquivo com campos tipados e deny_unknown_fields; caminhos relativos à pasta
do arquivo, variáveis preservam caminhos legados. Erros não imprimem conteúdo.
Limitar leitura do arquivo e recusar entradas inválidas antes de criar estado.

Escopo: configuração, main, monitor, testes unit/processo, exemplo e documentação,
registro P52. Sem novas quotas, listener adicional, MQTT5 ou mudança WAL/snapshot.
Preservar defaults existentes, mTLS, ACL, bundle privado, loops de laboratório,
RUST_LOG e instalação/env Ubuntu. Mudanças de arquivo exigem restart.

Aceite: legacy/TOML/overrides/caminhos/conflitos/validação negativos; configuração
inválida não cria estado; fmt/test/clippy/build, regressão C27/Will/shutdown.
Estado/serviços reais não modificados. Falhas exigem revisão deste prompt antes
de corrigir; resultado de gate registrado sem omitir tentativas.
Versão/tag/release somente após validação e decisão explícita nesta etapa.

## rev2 — revisão após análise de qualidade

Os 89 testes passaram; clippy recusou ausência de must_use em var_os e
conversão u64/usize no teste de tamanho. Corrigir com atributo e conversão
verificada, mantendo contrato e repetindo os gates. Isolar imports Unix nos
testes para preservar compilação Windows. Registrar a tentativa anterior.

## rev3 — revisão da documentação
A verificação de diff encontrou linhas vazias extras no fim dos documentos.
Normalizar os finais antes de repetir a verificação; nenhum contrato alterado.
