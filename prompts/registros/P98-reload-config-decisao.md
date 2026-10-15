# P98 — decisão B12 de reload geral

- Prompt [P98](../broker/98-reload-config-decisao.md) preparado antes do ADR.
- Decisão: [ADR-0006](../../docs/architecture/adr-0006-config-reload.md).
  TOML geral e campos de bind/perfil/estado/limites/monitor são restart-only;
  bundle privado conserva SIGHUP; B11 terá rotação TLS separada.
- Eventual reload geral exige validar e preparar todos os recursos antes de
  publicar um snapshot, recusando mudanças restart-only sem aplicar outros
  campos. Conexões TLS existentes não são alteradas pela troca de material.
- Validação documental: classificação e referências revisadas. Nenhum teste
  funcional foi usado como prova de runtime inexistente.
