# P265 v1.1 — validar configuração antes de iniciar o broker

Estado de entrada: broker 0.43.0 em `7c7a989e2eb567295e4674cc5303af19e13bce1e`.
Fases 6–8 aceitas no recorte documentado. Fase 9 permanece aberta. Alterações
de Manager, Oracle e histórico no checkout do usuário são preservadas.

Objetivo: `mqtt-broker --check-config` deve verificar a configuração efetiva
e os insumos de segurança de startup, sem abrir listeners nem modificar o
diretório de estado. A saída JSON deve incluir perfil e limites seguros para
inspeção, sem caminhos, credenciais ou conteúdo de arquivos.

Escopo: `src/main.rs`, testes de configuração, README, guia TOML e registro.
Reutilizar carregamento, precedência, validação dos perfis e loaders TLS/ACL.
A simulação não verifica disponibilidade de portas, conteúdo durável, tokens
do canal operacional ou capacidade de inicialização do serviço.

Compatibilidade: argumentos existentes, ACL, QoS, WAL/snapshot e schemas
preservados. Não requer migração. Validação pela conta e ambiente de execução.

Aceite: configuração válida retorna 0 e JSON redigido; configuração inválida
retorna 2 sem ecoar valores; arquivos e diretórios de estado permanecem
intocados. Cobrir override inválido, origem WSS incompatível e material de
segurança ausente. Fmt, testes e Clippy locked; registrar limitações de
plataforma e testar commit exato antes de marcar o marco. Tag de checkpoint
separada de versão publicada; release binária depende dos gates de pacote.

Revisão 1.1: o primeiro Clippy não estrito sinalizou tamanho de `run`.
Extrair a verificação de caminhos obrigatórios e a leitura do bind primário,
preservando a ordem das validações. A suíte geral no Windows encontrou bind 10013 e CRUD legado
Unix-only. Registrar esses bloqueios e usar a CI Linux para os gates gerais.
