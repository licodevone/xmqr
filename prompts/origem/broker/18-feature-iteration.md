# Prompt — iteração de feature

Feature solicitada: `<DESCREVA>`.

Leia contexto, ADRs, matriz de conformidade e código. Defina primeiro o comportamento observável e as cláusulas MQTT. Liste invariantes, estados, dados persistidos, limites, autorização, métricas e falhas.

Divida a feature na menor fatia vertical. Antes de editar, declare arquivos e testes. Implemente preservando compatibilidade; execute formatação, lint, unitários, integração e interoperabilidade relevantes. Atualize documentação e matriz normativa.

Ao aceitar o incremento, aplique versionamento semântico de acordo com `CHANGELOG.md`: registre versão anterior/nova, compatibilidade de protocolo, configuração e formato persistido; atualize `Cargo.toml`, `Cargo.lock`, documentação e notas de migração. Não aumente versão principal sem passar pelos gates correspondentes.

Entregue: resumo, versão, decisões, evidência, riscos residuais, itens deliberadamente fora do escopo e próximo incremento. Se uma escolha em `00-project-context.md` estiver indefinida e mudar a arquitetura, apresente opções e pare antes da decisão irreversível.
