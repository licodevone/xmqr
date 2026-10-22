# P250 — execução do diagnóstico de restart

22/10/2026. Prompt250v1.0 e P249v1.2 apresentados antes das alterações.

Imagem042302: trecho do roteiro; imagem042543 lida posteriormente confirma
Stopped Client, Start-Service falha antes de Restart-Service; Admin depois
Running. Não atribuir falha persistente ao restart rápido nem extrapolar SCM
atual a partir de captura anterior. Ferramentas: ElevatedFalse, SCM CimException,
lifecycle UnauthorizedAccessException. SHA instalado P248 correto:
e9228b317a9618ee7502b7aa007d822f48ad07b109e8ac85fceceb72e014bf51.
HTTP9090ready e9080authconfig recusados ativamente na consulta anterior à
nova imagem; não comprova status posterior do Admin mostrado Running.

Auditoria independente readonly Client: sem causa restart comprovada. Sink
abre arquivo existente sem truncar, validaLF/ACL/capacidade, cursorEOF correto;
OnceLockSINK/STOP são por processo. Running precede CONNACK, retry10 finito;
janela Stopped/saída pode causar corrida transitória, não explica persistência
sem evidência. Não alterar runtime/ACL/sink ou credenciais por hipótese.

Coletor ampliado: Sink.Exists/Length/EndsInLf/LengthUnchangedDuringRead,
limiteP247 de referência8388608 (não configuração real), ACL arquivo/state,
PIDSCM e listeners8883/9090/9080; mantém lifecycle sanitizado e sem conteúdo.
Parser PASS; quatro fixtures isolados vazia/LF/incompleta/ausente PASS,
retorno sem conteúdo; fixture sob target/p250-sink-GUID. Nenhuma coleta
administrativa real, serviço ou configuração instalado alterado.
P249 seção10 suspensa nas duas cópias;13blocos restantes parserPASS.

PENDING: operador executa coletor atualizado; consultar relatório novo no
workspace e então propor/corrigir causa comprovada. Antigo relatório22:37
não é evidência deste incidente. Sem commit/push/tag.

Relatorio novo04:27:53UTC lido. Causa suficiente do acesso negado estabelecida:
parentclient-default possui ACEexplicita aooperador, rejeitada porLocalService
antes da leitura do TOML. Sinkvazio/arquivosprivadosvalidos. Ver P251 para reparo
restrito preparado; aplicação120s pendente. Origemdaregra não comprovada.
