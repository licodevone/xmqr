# XMQR Manager Windows 0.1.1 — experimental

Gerenciamento local do Broker, Client e Admin instalados no Windows. O menu
permite iniciar, parar e reiniciar cada serviço ou o conjunto: inicia Broker
antes dos consumidores e para na ordem inversa. Reiniciar o conjunto para os
serviços antes de iniciá-los novamente. Erros interrompem a sequência e indicam
possível execução parcial; não há transação nem rollback automático.

Atalhos protegidos solicitam UAC quando o acesso é negado. A configuração
registrada abre no editor com o token administrativo; pastas protegidas abrem
no navegador de consulta do Manager, sem alterar ACLs ou seguir links/junções.
Os erros aparecem em janela independente do menu da bandeja.

A versão 0.1.1 permite atualizar o Manager 0.1.0 pelo MSI. A instalação ou
atualização do Manager não substitui os pacotes Broker/Client/Admin. Não reinicia
serviços automaticamente; execute os comandos pelo menu após a instalação.

Validação do recorte: 20 testes Rust, fmt, Clippy, build release, MSI/WiX,
probes e navegador WinForms com fixtures próprias. CI da tag/commit é registrada
no [P256](../../prompts/registros/P256-manager-releases.md). Binário, MSI,
checksums e proveniência correspondem à fonte exata dessa publicação.

Limites: UAC real, controle dos serviços reais, instalação/upgrade/rollback,
boot/login e DPI ainda não homologados no desktop. Verde/Running indica estado
SCM, não prontidão MQTT. Pré-release experimental, sem homologação de produção.

Código próprio MIT; notices das dependências acompanham o pacote e o arquivo
de distribuição. [Guia do Manager](../../tools/windows-manager/README.md).
