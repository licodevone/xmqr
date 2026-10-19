# P235 v1.0 — implementação e aceite integrado da fase 8/T02

Data: 2026-10-19. Pedido: «implemente a fase 8». Entrada broker `70da225`,
client `6baeeec`/0.42.1 com bridge 0.4.0; admin 0.11.0. Git limpo.
P223–P225/C125–C146 comprovam fatias anteriores, não o aceite global T02.

Objetivo: concluir as capacidades pendentes da bridge independente e sua
distribuição, preservando os contratos existentes. Funcionalidades ficam no
client; o broker/admin só mudam se houver necessidade demonstrada por teste.
Cada fatia terá prompt próprio antes do código e registro real após execução.

## Requisitos que precisam de prova para fechar a fase

1. Configuração compatível com v1 e opção de múltiplos mapeamentos limitados,
   identidades/sessões/journals independentes por rota e diagnóstico estático.
   Recusar sobreposição ambígua, rota ausente da topologia, limites e permissões.
2. Origem/destino MQTT 5 para propriedades: PFI, Content Type, Response Topic,
   Correlation Data, User Properties com ordem/repetições e Message Expiry sem
   renovar TTL durante fila/retry. Alias/Subscription Identifier são locais à
   conexão e não podem ser copiados como metadados de aplicação. Remapeamento
   de Response Topic deve ter política explícita. Preservar os modos 3.1.1.
3. QoS 0/1/2, inclusive publicação com QoS menor que o da assinatura, retained
   inicial/vivo e retenção removida por payload vazio. A confirmação em cada
   perna MQTT não é recibo de processamento de negócio.
4. Estado privado durável do encaminhamento, incluindo payload/metadados e
   fase da publicação no destino, antes dos ACKs correspondentes. Recuperar
   quedas nas janelas definidas, impor limite e identidade/versão, preservar
   arquivo corrompido/incompatível e falhar fechado quando faltar sessão.
   Formato antigo deve continuar legível ou ter migração/rollback explícitos.
5. Proteção de percurso por mensagem para topologias externas MQTT 5: marcador
   limitado de identidade/percurso e teto de saltos, recusa de retorno e de
   marcação inválida; teste com encaminhador externo que preserve propriedades.
   Conservar o guardião acíclico do manifesto para conexões legadas. Não
   prometer detectar intermediário que apague a marcação: essa fronteira deve
   ficar explícita na configuração/documentação e nos negativos do aceite.
6. Reconexão limitada, identidade estável, ACL/CA/SAN/senha/mTLS, quotas e ACKs
   negativos tratados sem confirmar obrigação perdida. Não logar dados ou
   segredos; disco/hash bloqueantes seguem as fronteiras Tokio apropriadas.
7. Matriz com XMQR↔XMQR, XMQR↔Mosquitto nos dois sentidos, múltiplas rotas,
   cadeia e retorno externo, reinício/crash, retained/propriedades/expiração e
   negativos. Gates Rust/CI e ELFs do pacote/imagem da fonte exata.
8. Versão independente do client/bridge, pacote Ubuntu26 amd64, instalação/
   rollback descartáveis, imagem numerada, tag/release imutáveis e hashes
   remotos conferidos. Atualizar plano, T02 e matriz de aceite honestamente.

## Fronteiras do contrato

O journal transacional local precisa tornar o encaminhamento recuperável.
Ele não cria commit atômico distribuído entre dois brokers independentes:
replay após resultado remoto incerto pode duplicar entre as pernas. Esse
limite não autoriza perda silenciosa, ACK prematuro ou ignorar as janelas de
crash. Os testes devem mostrar o comportamento e a identidade da mensagem.
MQTT 3.1.1 não transporta User Properties; a preservação completa de metadados
e a proteção de percurso exigem MQTT 5 nas pontas correspondentes. Configuração
incompatível deve ser recusada ou exigir descarte explícito, nunca silencioso.

Não fechar T02 por quantidade de prompts/testes. Marcar concluído somente
após confrontar cada requisito acima com implementação, execução e entrega.
Windows/fase 9, cluster e certificação MQTT integral ficam em seus contratos.
