# P62 — baseline inicial da fase2

Base d7b9d41/tagv0.11.0, árvore limpa. Skill xmqr-tests aplicada; promptrev1
criado/apresentado antes do harness. Sem alteração runtime/client ou versão.

Ensaio inicialPASS:3repetições,200 mensagens; /tmp=tmpfs, janelas19–25ms.
Dados inadequados para medirCPU/disco representativo; não são baseline publicada.
Rev2 precedeu --state-root,2000mensagens/100warmup e retained com sequência
variável. Ensaio nativo /home Ubuntu26/WSLPASS:12cenários,6000PUBACKs específicos,
shutdown0 por cenário e cleanup de processos/diretórios temporários.

Ambiente/results em docs/results/p62-baseline-2026-10-11.json. Hardware:
IntelCoreUltra7 155H; storage reportado ext2/ext3 nativoWSL. Fonte/runtime e
manifest sem alterações, binárioSHA confirmado. RSS idle32 mediano cerca6MiB;
QoS1retained sequencial192,7–228,0mensagens/s. Não significa máximo, TPS de
aplicação, entrega a assinante, consumo comTLS ou RAM por cliente extrapolável.

Rev3 corrigiu campo de timestamp do fim para completed_utc no harness e na
cópia documental, sem alterar números; JSON inicial preservado emtarget.
Hash do harness de medição reconstruído pela única mudança de chave indicada.
CPU emticks pode medirzero para idle sem provar consumo absolutamentezero.

Gates: execução real, JSON12cenários/6000ACKs, hashbinário, syntaxPython,
negativos de argumentos inválidos/sobrescrita, links e diff. Rust não repetido
porque nenhum fonteRuntime/manifest mudou. Commit/push; sem tag/release para
baseline inicial. Não modificou instalação/credenciais/estado do operador.
Próximo prompt para cargasQoS0/1/2, fan-out/TLS e janela sustentada; não executado.
