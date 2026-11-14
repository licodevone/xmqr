# P281 v1.0 — instaladores Broker 0.45.0

Base `e8712bfcf885e3b12ce59173e1a483f5de58b5b5`. O workspace contém
alterações separadas do Manager e registros locais. O aceite da versão
e a publicação do P279 continuam pendentes.

- Gerar o `.deb` Ubuntu 26.04 amd64 e o `.msi` Windows x64 a partir
  de cópias isoladas dos commits de validação do Broker e do Client.
- Usar `scripts/build_deb.py` e `scripts/build-windows.ps1`, com os
  manifests de serviço e lockfiles versionados. Preservar dados,
  configuração, identificadores de upgrade e verificações de licenças.
- Validar os metadados de versão, o conteúdo e os SHA-256 dos pacotes
  gerados. MSI exige o probe do adaptador de serviço. Testes de instalação
  e upgrade exigem ambiente descartável separado do host instalado.
- Registrar arquivos e bloqueios em `prompts/registros/P281-instaladores-045.md`.
  Artefatos sem aceite completo são experimentais. Não instalar serviços
  nem promover tag ou release pendente como consequência do build.
