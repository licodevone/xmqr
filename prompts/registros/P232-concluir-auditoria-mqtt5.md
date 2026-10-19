# P232 — auditoria concluída com achados

Prompt [P232 v1.8](../broker/232-concluir-auditoria-mqtt5.md), autorizado pelo
pedido de prosseguir até finalizar a auditoria com gestão de modelos e
publicação quando apropriada. Data do operador: 18/10/2026, America/Sao_Paulo.

## Estado e preservação

Broker inicial `4bfac0722074c7a1f704f335d2d1b558e68e3d6b`, limpo e origin/main
igual. A CI geral P231 `39177141768` terminou SUCCESS na fonte4bfac;
não ficou pendente. Runtime 0.43.0. Client `e03c5a46cfb33666896eb710892cf46e3c40ee38`,
cache não rastreado vendor/rumqttc-0.25.1/target preservado. Admin
`0796d3b4d93ae6815fe2458132f1f8bf0c5c48e4`, sem mudanças.

Durante a auditoria apareceu commit local `1a4b0a7`, contendo o próprio prompt
P232 v1.0 preparado nesta execução. Não foi criado pelo coordenador nem pelos
agentes delegados desta rodada. Foi preservado, sem reset/reescrita; as revisões
v1.1–v1.8 são alterações posteriores do prompt. O remoto ainda estava em4bfac
quando essa diferença foi constatada. Não houve mudança paralela de runtime.

Nenhum código Rust, manifest, licença, configuração global, segredo, serviço
operacional ou hardware foi alterado. Não houve instalação, build, mudança
de firewall ou acesso a C:/x81. A pasta consumidor mqtt-broker permanece fora
do núcleo XMQR e fora desta auditoria.

## Gestão real de modelos e autoria dos arquivos

- Sol/high, `p232_connect_auth`: ledger CONNECT/CONNACK/AUTH,87 IDs.
- Sol/high, `p232_publish_subscribe`: ledger publicações/assinaturas/tópicos,101 IDs.
- Sol/high, `p232_session_flows`: ledger sessões/QoS/fluxos,48 IDs.
- Coordenador: representação/transporte,16 IDs; ferramentas, probes, evidências
  e parecer. Cada agente escreveu apenas seu ledger; ninguém delegado fez Git.
- Luna/high, `p232_mechanical_luna`: revisão mecânica de accounting/probes.
- Astra/high, `p232_independent_astra`: revisão cruzada de252 resumos,
  37 revisões por seção, achados e amostras dirigidas da norma/código.

Os revisores não executaram testes. Todos os resultados de execução abaixo
são do coordenador. A revisão Astra não foi uma segunda auditoria exaustiva
independente de cada implementação. Não foi trocado o modelo principal nem
alterada configuração global de modelos.

## Cobertura e conclusões

Quatro ledgers:252 IDs/504 classificações por papel,37 revisões não numeradas,
20 registros de achados com sobreposições. Broker220 suporte por inspeção,
2 lacunas,30 N/A; client115 suporte por inspeção,18 lacunas,5 desvios,114 N/A.
Todo N/A tem justificativa; suporte por inspeção não significa teste PASS.
O catálogo mecânico P231 permanece com seu templateUNREVIEWED; não representa
revisão semântica pendente, pois essa está nos ledgers próprios P232.

Os cinco desvios obrigatórios do client foram reproduzidos: MaximumQoS,
RetainAvailable, SessionPresent sem estado local, duplicação de entregaQoS2
e falta de PUBCOMP para PUBREL repetido. Quatro recomendações de recepção
falharam separadamente; nove FAILs de probes não viraram nove violações MUST.

Revisão Astra corrigiu três interpretações antes do fechamento:

1. Takeover sem0x8E: MUST explícito é fechamento, confirmado. Notificação
   ausente ficou recomendação/interpretação, não desvio obrigatório do broker.
2. DUP/aliases/quota de requests pending na biblioteca: sem alcançabilidade
   comprovada na CLI, classificados como lacuna/dependency-only.
3. Client§4.13.1 usa SHOULD para resposta a pacote inválido, diferentemente
   do Server. Removido ID inexistente MQTT-4.13.1-2 dos achados finais;
   probes de servidor falso não provam emissão inválida pelo client.

Parecer: [auditoria concluída com achados](../../docs/conformance/mqtt5-audit-final.md),
conformidade integral do client refutada nos cinco vetores; conformidade
integral do broker não demonstrada. Não é certificado nem prontidão de produção.
Correções futuras são novas entregas; não foi preciso tornar todos os testes
verdes para concluir uma auditoria com parecer negativo.

## Probes reais, controles e falhas mantidas

WSL Ubuntu-26.04/Python3.14.4, portas efêmeras em127.0.0.1, diretórios privados
em/var/tmp nativo ext2/ext3 e cleanup. ELFs dos pacotes publicados:

- broker043 fonte db472bc, SHA1ee611b082b5e8cb14bf881996ce314c391573353cf8971232728cb54a243207;
- client041 fonte1d60d38, SHAb9f2fa67c4c4d7263966097cd048627929b59d161b436d1b23e6005edac872f0;
- deb client041 SHAca68df0788d62ec2d63701eea07e63a168f4cdc26b0bbd10142dc163f686e6a7,
  conferido antes de extrair sem instalar.

Comparação Git do runtime broker db472bc→4bfac vazia. No client1d60→e03,
CLI/vendor/Cargo iguais; mudanças em mqtt-bridge.rs/bridge_journal.rs excluídas
expressamente da igualdade. Não se atribuiu o ELF anterior à bridge atual.

1. Primeiro client probe:3PASS/7FAIL, exit1,0,743s. Controle sub usou SUBACK
   QoS2 para pedidoQoS0 por erro do harness; strings negativas dessa execução
   não demonstram a validação pretendida. Promptv1.1 precedeu correção.
2. Relatório2:3PASS/7FAIL, exit1,0,810s. Controle sub corrigido PASS e tópico
   NUL aceito FAIL. Não apagado relatório1.
3. Relatório3:11 cenários,3PASS/8FAIL/0BLOCKED, exit1,1,060s; duplicaçãoQoS2
   observada por duas linhas JSONL para a mesma transação.
4. Após revisão Luna, relatório4 fortaleceu observação de tópico/payload no
   JSONL e separou categorias MUST/recomendação.11cenários,3PASS/8FAIL,
   exit1,1,376s. Promptv1.4/v1.5 precedeu essa revisão.
5. Promptv1.6 acrescentou retomada sem estado local. Relatório5:
   **12 cenários,3PASS/9FAIL/0BLOCKED**, exit1,1,015s;5MUST_FAIL e4recomendaçõesFAIL.
   Os3PASS são pub/sub canônicos e rejeição de tópico UTF-8 malformado.
   A falha é resultado real do produto, não falha de instalação ou permissionamento.
   Revisão final Astra aprovou a coerência do parecer delimitado, sugerindo
   apenas não chamar de legítima a retransmissão arbitrária na mesma conexão.
   Promptv1.7 corrigiu comentário, sem alterar o oráculo. Relatório6 final:
   mesmos12cenários/3PASS/9FAIL/0BLOCKED, exit1,1,153s; hash do harness final
   3c02cdfa5e8c526de2072954acb21779aaaadffa37ad1dd239ba5003c1b5011d.
6. Broker VBI:21/21PASS, exit0. Broker aliasReason:9/9PASS, exit0.
7. Broker closes1 e2:3/3 fechamentos obrigatóriosPASS, nenhum diagnóstico,
   nova conexão de takeover PINGPASS, cleanupPASS, exit0;0,169s cada.
   Segunda versão acrescentou preflight Linux/filesystem, sem mudar o resultado.

`verify_p232_client_wire.py --client <ELF> --client-source-commit <SHA>
--report <NOVO_JSON>` executou apenas servidor falso privado e o client.
`verify_p232_broker_closes.py --broker <ELF> --report <NOVO_JSON>` usou
Laboratory isolado; VBI/alias usaram os scripts existentes com `--state-root
/var/tmp --label candidate --report <NOVO_JSON>`.

Os hashes dos dez relatórios imutáveis e resultados resumidos estão em
[evidências](../../docs/conformance/mqtt5-audit-evidence.json). Originais locais
fora do Git em../.artifacts; nenhum segredo real, payload operacional ou
certificado privado foi necessário. Hash é integridade observada, não assinatura
ou atestado de terceiro.

## Accounting e QA

Primeiro validador:9 contratos sintéticosPASS; ledger realFAIL em
MQTT-3.3.1-3/client, applicability/statusN/A inconsistentes. Promptv1.3 registrou
antes da correção semântica de60 paresN/A da partição. Não afrouxar enum/oráculo.
Após correção:252/504/37, exit0. Fortalecimento Luna: campos exatos, listas,
bool/inteiro, chaves únicas, referências e ausência de ID normativo inventado.
Contratos finais:13/13PASS em Windows; inventário P23116/16PASS. Contagem não
é avaliação de qualidade ou percentual MQTT.
Repetição final em WSL:16/16 e13/13PASS, ledger252/504/37 exit0;64links
locais sem falhas, dez hashes de relatório conferidos, hash do harness final
igual ao relatório6, AST dos quatro scriptsPASS, workflow YAML/pin/permissões
conferidos, diff --checkPASS. Metadados dos quatro ledgers congelados no JSON
de evidências. Esses checks não promoveram as nove falhas do client a PASS.
Gate staged posterior encontrou EOF com linha em branco extra no ledger
publish-subscribe (diff de worktree anterior não incluía esse arquivo ainda
não rastreado). P232v1.8 precedeu normalização de EOF e atualização do hash;
repetir staged check antes de publicar, sem alterar julgamento ou testes.

CI offline atualizada com checkout do client público no pin auditado para
validar caminhos irmãos; não copia cache local nem executa serviços/probes.
Ela verifica schema/accounting/fontes dos probes, não normatividade semântica
ou prova dinâmica universal. Resultado remoto deve ser lido no commit publicado.

Não repetir fmt/Rust/interop/hardware apenas para documentação e novos scripts;
histórico69/69 da CI39164217059 permanece preso a db472bc/501cde2/4483a35.
Essa campanha histórica não foi promovida a execução atual de peers novos.

## Publicação

Commit/push dos próprios arquivos aceitos autorizados. Preservar commit local
do prompt já existente. Auditoria não mudou runtime: sem bump/tag/release,
.deb ou imagem Docker artificiais; tags e latest antigos intactos.
MIT autoral e licenças da OASIS/dependências mantidas separadas.
