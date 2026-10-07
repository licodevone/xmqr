# Prompt — escopo e ADRs

Leia o contexto central. Transforme requisitos em uma matriz de escopo com colunas: capability, versão MQTT, MVP/futuro/fora, dependências, risco e evidência esperada.

Crie ADRs apenas para decisões com alternativas reais: runtime e modelo de concorrência; limites entre crates; representação do codec; índice de assinaturas; persistência e durabilidade; configuração; autenticação/ACL; observabilidade; compatibilidade de dados. Cada ADR deve conter contexto, forças, opções, decisão, consequências e gatilho de revisão.

Não escolha cluster, plugin ABI ou abstrações distribuídas antecipadamente. Termine com um mapa de riscos ordenado por incerteza técnica e custo de reversão.

