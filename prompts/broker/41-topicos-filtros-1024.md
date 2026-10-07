
# P41 — Alinhar tópicos/filtros a 1024 bytes UTF-8

Versão 1.0. Pedido autorizado após concluir P-DOC-02. Estado de entrada:
broker 256 bytes, CLI 1024; configuração/skills concluídas e validadas.

## Prompt de trabalho

No XMQR, amplie somente tópico/filtro para 1024 bytes UTF-8. Prepare este prompt
antes de editar código. Centralize o limite em constante compartilhada pelo broker
e CLI. Preserve validadores de nome/filtro, wildcard, $, nulidade e ausência de
normalização. ACL e restore usam os tipos comuns e devem aceitar o novo limite.
Não mudar quantidade de assinaturas, sessões, payload, pacote, senha, filas,
inflight ou quota do documento. Não implementar Client ID, Will, MQTT 5 ou consumidor.
Atualize documentação e instruções ativas sem reescrever originais/histórico.
Acrescente testes de 1024 aceito/1025 rejeitado em ASCII e UTF-8 multibyte:
tipos, wire PUBLISH/SUBSCRIBE/UNSUBSCRIBE, CLI, ACL e roteamento/restore.
Os formatos WAL/documento permanecem v1, mas estados com nomes >256 não são
legíveis pelo snapshot anterior. Documente backup completo e rollback antes de
gravar nomes longos; não apagar nem migrar o estado real do usuário.
Confirme MQTT-4.7.3-3/4 e §1.5.3 na OASIS: 1024 é quota local, não máximo MQTT.
Execute fmt, cargo test --locked e clippy; inventário e interop pertinentes se
ambiente existente permitir, sem instalação. Use somente esta cópia de trabalho
para os testes, nunca o clone WSL anterior. Sem commit, release ou implantação.

## Aceite e evidência

Broker/CLI no mesmo contrato de 1024 bytes; multibyte contado em bytes;
fronteiras e caminhos relevantes testados; limites não relacionados preservados.
Registro em ../registros/P41-topicos-1024.md com passes/falhas/bloqueios reais.
Fonte: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html

## Retomada de validacao - versao 1.1, 2026-10-07

Rust 1.99 confirmado no Ubuntu-26.04. Validar a mesma copia via
/mnt/d/projects/my-project/xmqr, sem usar clone anterior. Executar fmt, testes,
Clippy e inventario; testar pub/sub 1024 bytes UTF-8 com mqtt-client proprio,
retained apos reinicio e recuperar nomes longos. Recursos de teste isolados.
Nao instalar Mosquitto; gate externo especifico fica NOT_RUN. Investigar logs
CI run37393863354 sem alterar remoto. Corrigir somente falhas de P41; relatar
falhas preexistentes. Atualizar registro/JSON com evidencias reais. Sem Will,
commit, push, tag, release ou alteracao do estado real do usuario.
