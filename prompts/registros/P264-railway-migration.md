
## Preparação inicial — 2026-11-07

- SSH autenticado na instância Oracle. Inventário sem copiar segredos para saída.
- Criado serviço vazio xmqr-broker no projeto Railway xmqr-platform-postgres / production.
- Criado volume persistente em /var/lib/xmqr no serviço novo.
- Oracle preservada e em execução. Nenhum deploy, proxy TCP, certificado ou estado foi migrado ainda.
- Bloqueios restantes: configurar secret files/ACL e TLS/SAN para domínio Railway, deploy, proxy TCP, backup consistente e testes interoperáveis. Admin/Manager ainda precisam da configuração do novo endpoint.
