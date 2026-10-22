# P246 - Icones XMQR, atalhos e diagnostico

Versao 1.4 - 21/10/2026, America/Sao_Paulo.

Revisao 1.4: usuario pediu nome Admin/Client/Manager maior e XMQR pequeno
embaixo, depois reiterou reduzir XMQR. Variante final usa assinatura XMQR
aproximadamente um quarto da largura, com nome dominante. Clippy do Manager
detectou chunks_exact_to_as_chunks no tratamento RGBA; aplicar as_chunks_mut
sem suprimir o lint e repetir somente os gates afetados antes do build final.

Revisao 1.3: prova isolada da API UpdateResource insere .rsrc e desloca apenas
o RVA de .reloc nao executavel, mantendo todos os bytes/tamanhos/flags de .reloc
identicos e corrigindo o ponteiro da tabela de relocacao. Permitir somente esse
deslocamento, se a tabela continua apontando para os mesmos bytes/tamanho.
As demais secoes nao-resource exigem igualdade de conteudo, RVA, tamanhos,
flags e entrypoint. Sem relaxar padding, codigo, dados ou assinaturas.

Revisao 1.2: ferramenta de imagens recusou o formato de caminho Windows antes
de executar. Usar a imagem anexada na conversa como referencia visual para
gerar as variantes; nao alterar artisticamente o logo por script. Conversao
deterministica de PNG para ICO/RGBA sera feita por .NET para recursos Windows.

Revisao 1.1: screenshot inspecionado mostra codigo SCM1077, que significa
nenhuma tentativa de inicializacao desde o ultimo boot. Corrigir a classificacao
do gerenciador para Ainda nao iniciado; nao confundir com falha comprovada.
Adicionar teste da traducaode estado e manter falhas reais/consulta negada.
Recursos PE podem ser aplicados por API nativa UpdateResource em COPIAS
dedicadas dos payloads P243, sem rebuild Rust dos tres servicos: origem/hash,
assinatura ausente, integridade de secoes de codigo e capability devem ser
conferidos; nao modificar executaveis instalados ou inputsextraidos. Manager
precisa novo build por alterar status; fazer build apenas dele com cachegravavel.
Aplicar ico como recurso PE e embutir sua versao RGBA no Manager para bandeja,
mantendo cor verde/apagada conforme estado. Nao desativar validacoes de TLS.
Pedido: programas sem atalhos/funcionamento; aplicar segunda imagem (logotipo
XMQR) no Broker e criar variantes Admin, Client, Manager para os demais.

Entrada: HEAD 0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed; preservar alteracoes
P244/P245 e chat. P245 alterou apenas instaladores; nao consertou servicos.
Nova imagem mostra os tres componentes em Falha. Nao ha relatorio P244 local.

## Escopo autorizado

- Materializar logotipo enviado e screenshot; inspecionar antes de editar.
  Criar variantes de marca via ferramenta de imagens e converter formatos de
  recursos Windows. Broker mantem XMQR sem sufixo; demais possuem seus nomes.
- Instalar icones por componente nos atalhos, Aplicativos e executaveis quando
  a ferramenta nativa permitir. Preservar licencas e origem dos executaveis.
- Corrigir opcao de atalhos: desktop e menu Iniciar marcados por padrao,
  escolhas explicitas preservadas. Nao depender de indice da pesquisa para
  concluir existencia de atalho. Explicar e testar fluxo do gerenciador.
- Diagnosticar servicos existentes com consultas somente leitura; acesso
  negado nao prova causa nem inexistencia. Nao iniciar, parar, reinstalar,
  alterar ACL, gerar credenciais ficticias ou relaxar TLS automaticamente.
- Revisar coletor/entrega para obter erro concreto se leitura administrativa
  continuar bloqueada. Mostrar condicoes de provisionamento com evidencia.

Arquivos: assets Windows novos, packaging/windows, scripts de build/recursos,
verificadores existentes, docs e registro P246. Alteracoes de runtime limitadas
a diagnostico/icone; revisar prompt antes de expandir. Paralelizacao autorizada
na conversa: diagnostico independente e empacotamento, sem disputar arquivos.

## Aceite

PNG/ICO de quatro marcas inspecionados; estrutura ICO multi-resolucao valida.
MSIs compilados e auditoria somente leitura de icones, atalhos e opcoes.
Quando executaveis receberem recursos, conferir PE/capability e origem/hash;
nao afirmar novo build Rust se forem payloads P243 com recursos atualizados.
Registrar a causa comprovada dos servicos ou a consulta bloqueada e entregar
coletor executavel com resultado acionavel. Nao repetir instalacao como solucao
de falha de configuracao. Manter o chat. Sem commit/push/tag/versao/release.
