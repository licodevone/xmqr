# P243 - Assistente, atalhos e aceite de licença Windows

Prompt: [P243 v1.4](../broker/243-windows-installer-discovery.md).
Data: 21/10/2026, America/Sao_Paulo. Pedido inicial: investigar instalação com
UAC, sem etapas/conclusão e sem software pesquisável; pedidos seguintes:
avaliar raiz C, solicitar atalhos e oferecer aceite de termos de licença.

## Diagnóstico comprovado

Os quatro MSIs P242 foram abertos em modo somente leitura pela automação COM
WindowsInstaller.Installer/OpenDatabase(0). Todos tinham InstallUISequence,
mas nenhum tinha tabela Dialog ou Shortcut. Os fontes também não declaravam
UI/Shortcut. `install-windows.ps1` usava `/passive` e janela Hidden; o MSI do
manager registrava HKLM Run para o próximo login, sem atalho pesquisável.
Um MSI individual de broker/client/admin não instala o gerenciador.

Isso explica a ausência de assistente e atalhos. Não comprova sucesso ou falha
da tentativa específica do usuário. Nesta sessão, caminhos e chaves padrão de
XMQR não apareceram, e SCM e eventos MsiInstaller negaram acesso. Não interpretar
essa limitação como inventário completo de outro contexto/usuário ou aceite SCM.
O anexo image.png foi referenciado, mas não ficou acessível pela leitura tentada;
o diagnóstico acima usa fontes, tabelas MSI e consultas locais somente leitura.

## Correções

- UI WiX compartilhada, sem extensão nova: boas-vindas com ProductName,
  Instalar, progresso modeless com assinaturas ActionText/ActionData/SetProgress,
  Concluir, confirmação de cancelamento, cancelado e erro terminal. ErrorDialog
  preserva `[Error]` e botões padrão do protocolo Windows Installer.
- Menu Iniciar marcado por padrão e Área de Trabalho opcional. Manager tem seus
  próprios atalhos; componentes têm nomes de produto distintos e abrem o manager
  já registrado em HKLM 64-bit. As condições impedem alias sem manager. Nenhum
  atalho executa --control nem inicia serviço. HKLM Run foi preservado.
- Aceite de licença desmarcado, botão Ler termos e texto rolável RTF. Instalar
  exige aceite explícito em instalação nova. Propriedade segura segue para o
  processo elevado; modo passivo/silencioso novo exige aceite explícito também.
  Manutenção/remoção permanece possível sem novo aceite.
- `TERMS.pt-BR.txt`/RTF apresentam a licença e informações de instalação; MIT
  original preservada integralmente, com autoria real do LICENSE. Nenhuma nova
  restrição comercial, foro, CNPJ ou política de privacidade foi inventada.
- Coordenador usa `/qf` por padrão, deixa `/passive` opt-in, distingue códigos de
  sucesso, cancelamento1602 e falha; grava logs e result.json no LocalAppData do
  usuário, e verifica registro/arquivo de cada pacote após sucesso MSI.
- Launcher `Instalar-XMQR.cmd` permanece aberto no fim/erro. Diagnóstico
  `diagnose-windows.ps1` é somente leitura; não usa Win32_Product nem lê segredos.
- Diretórios conservados: Program Files/XMQR para programas e ProgramData/XMQR
  para dados. Nenhuma DACL privada aplicada à raiz C ou a pasta arbitrária.

## Validação e ocorrências

Builds reutilizam as fontes/locks congelados P242, sem alterar versões e sem
novo gate de protocolo. Executáveis são comparados por hash ao pacote P242,
cuja prova nativa release de 12 cenários já está documentada. Esta fatia altera
instaladores e scripts; não declara nova interoperabilidade nem aceite de UI real.

- Primeira suíte de empacotamento: falhou ao usar Get-FileHash indisponível no
  Windows PowerShell5 desta sessão e ao consultar Shortcut ausente em MSI de
  componente. Coordenador passou a usar SHA256 .NET; auditoria passou a consultar
  tabelas conforme o pacote. Negativos de preflight confirmam recusa antes de
  qualquer lançamento de instalador, com Start-Process substituído por sentinela.
- Auditoria detectou ErrorDialog.Control_First=Y; ErrorText tornou-se o primeiro
  controle conforme o protocolo. MSIs recompilados e auditados novamente.
- Revisão impediu colisão de `.lnk`: aliases dos componentes usam ProductName,
  preservando o atalho XMQR Manager pertencente ao seu MSI separado.
- Resultados provisórios R1/R2 foram superados pelos pedidos de atalhos e licença;
  seus diretórios foram preservados e não são a entrega atual.
- Falha intermediária no auditor de RegLocator/COM foi corrigida no helper;
  os resultados finais usam a versão completa congelada, sem editar durante gates.
- O primeiro teste de licença procurava a Property no fragmento UI; ela pertence
  aos Packages. Corrigido o teste. O botão passou a ter DisableCondition inversa
  explícita, além do estado inicial desabilitado e Publish condicionado; atalhos
  exigem valor textual "1" em vez da presença da propriedade.

## Resultado final

`python scripts/verify_windows_packaging.py --wix`: **17/17 PASS**, incluindo
quatro builds MSI de fixture e inspeção de tabelas compiladas. Build completo
offline dos quatro produtos: PASS em `dist/windows/candidate-p243-final-20261021`.
Os quatro MSIs reais também passaram, individualmente, o auditor
`verify_windows_installer_ui.ps1` em modo OpenDatabase(0), sem instalar.
Os quatro hashes de executável coincidem com P242; fontes Rust/locks preservados.
`git diff --check`: PASS. README do candidato coincide com a fonte atual.

O auditor confere conteúdo MIT incorporado no ScrollableText, aceite inicialmente
vazio, abrir/fechar termos, habilitar/desabilitar Instalar, guarda passiva e
transferência segura da propriedade para a instalação por máquina. Também
confere alvos, nomes únicos e condições dos atalhos de menu/desktop, progresso
modeless, ErrorText primeiro e rotas de sucesso/cancelamento/erro.

Os termos foram gerados em TXT UTF-8 e RTF com escapes Unicode, incluindo a MIT
original integral. Não se promoveu uma licença nova nem alterou o LICENSE.

Resultados finais, hashes e caminhos são registrados em
[p243-windows-installer-discovery-20261021.json](../../docs/results/p243-windows-installer-discovery-20261021.json).
Nenhum serviço ou MSI foi instalado, removido ou reiniciado no host; sem
commit/push/tag. Interação UAC, criação efetiva de atalhos, clique nos diálogos,
instalação/rollback/boot/SCM real permanecem NOT_RUN em VM elevada indisponível.

## Entrega

ZIP final: `dist/windows/XMQR-Windows-P243-licenca-atalhos.zip`, 9.464.673 bytes.
SHA-256: `021b98946025aa593c67e5cc7dda20950abf7c5fe88148c283e8be29438ebcb3`.
CRC e 1.037 checksums internos PASS. Auditoria dos MSIs reais: manager 57
verificações PASS; broker/client/admin 60 cada. Inclui quatro MSIs (três produtos
e o gerenciador auxiliar compartilhado), launcher, coordenador, diagnóstico,
termos TXT/RTF, notices, README e manifesto; sem WixPDB, credenciais ou estado.
O usuário abre `Instalar-XMQR.cmd` após extrair o ZIP completo, e escolhe atalhos
e aceite nos assistentes. A instalação atual do usuário não foi substituída.
