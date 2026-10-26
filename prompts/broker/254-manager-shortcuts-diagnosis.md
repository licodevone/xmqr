# P254 — Diagnóstico dos atalhos do XMQR Manager

Versão 1.0, 2026-10-25. Pedido: verificar por que as opções de configuração,
pastas de configurações, certificados e logs dos três componentes não abrem.

Entrada: broker HEAD `654410c`; alterações anteriores em docs/chat preservadas.
Manager instalado em Program Files; componentes admin, broker e client-default
registrados no HKLM 64 bits. Sessão do diagnóstico sem elevação.

Objetivo: conferir os destinos registrados, distinguir acesso negado de caminho
ausente, revisar o lançamento e a apresentação de erros e consultar o painel
loopback sem autenticação. Produzir diagnóstico verificável antes de decidir
mudanças funcionais ou de instalação.

Escopo: leitura do inventário, metadados e permissões disponíveis; sondagem de
abertura de arquivos sem ler bytes e de enumeração sem registrar nomes; consulta
`--diagnose` do executável instalado e status HTTP da raiz do painel. Evidências
sanitizadas em docs/results e registro em prompts/registros/P254-*.md. Histórico
do chat conforme AGENTS. Não ler configurações, certificados, chaves ou logs.

Não instalar, elevar, modificar ACLs/serviços, iniciar/parar componentes, trocar
binários, publicar ou alterar versões. Não corrigir política de acesso apenas
para contornar o erro observado. MQTT, configuração e estado persistente intactos.

Aceite: separar resultado por componente/atalho, identificar caminho e categoria
de falha, conferir ferramentas do Windows e indicar o limite da prova de clique.
Falha de metadados com acesso negado não prova inexistência. Sucesso de criação
do Explorer não prova abertura da pasta. HTTP 200 não prova login ou MQTT.

Validação proporcional: sondagens nativas somente leitura e revisão dos trechos
responsáveis do Manager; git diff --check dos documentos. Gates Rust e interop
não aplicáveis a esta etapa documental sem alteração de código.

Correção funcional e aplicação instalada permanecem trabalhos posteriores ao
diagnóstico, sem presumir autorização para alterar permissões ou instalação.

## Complemento v1.1 — revalidação em sessão elevada, 2026-10-25

Estado de entrada: mesmo HEAD e alterações locais preservadas. Nesta sessão,
o token do agente é administrativo; resultados não equivalem aos do Manager
iniciado normalmente no login. Objetivo: confrontar o diagnóstico anterior com
inventário, acesso efetivo atual, ACLs, serviços e disponibilidade HTTP.

Escopo/arquivos: acrescentar evidências e limites ao registro P254 e aos
históricos diários; sem alteração funcional, de instalação ou de permissões.
Sondar abertura de configurações sem ler bytes e enumeração inicial de pastas
sem registrar nomes. Consultar ACLs sem expor identidades pessoais e tentar
localizar a interface pela skill computer-use. Aceite: distinguir claramente
prova anterior sem elevação, prova atual elevada e cliques não reproduzidos.
Compatibilidade/migração: nenhuma. Validação: sondagens somente leitura e
git diff --check; gates Rust não se aplicam a alterações documentais.
