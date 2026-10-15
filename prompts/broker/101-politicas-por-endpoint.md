# P101 rev1 — B09: política estática por endpoint mTLS

2026-10-15. Entrada: broker0.13.1 publicado; P100/B11 validado localmente,
ainda sem tag. Pedido do mantenedor: concluir a fase 4, mantendo prompt antes
da funcionalidade, plano marcado e repositório/release atualizados.

Objetivo: permitir que o primário e até três endpoints mTLS adicionais tenham
arquivos estáticos de usuários/ACL próprios, sem roteador, armazenamento ou
limite de conexões duplicados. A opção explícita `[[endpoint_policies]]` do TOML
v1 mapeia cada bind declarado a `users_file` e `acl_file`; todos os endpoints
devem estar presentes exatamente uma vez. O modo legado e o bundle dinâmico
conservam política compartilhada; rejeitar mistura de bundle com escopos.

Isolar principal e client ID persistidos por índice do endpoint. Reuso do mesmo
nome/ID em outro endpoint não deve assumir sessão/ACL alheia. Marcar o estado
como perfil separado `secure-mtls-scoped`; recusar diretório de estado antigo
em vez de migrar ou apagar dados. A política global do roteador revalida ACL de
publish, subscribe, retained, replay e Will para o escopo original. O servidor
não altera QoS/bytes wire, TLS, quotas ou o contrato SIGUSR1 de P100.

Aceite: configuração completa e falhas de índice/bind/campo/arquivo, positivo
cross-endpoint com IDs iguais e ACLs diferentes, negativos de autenticação e
ACL, restart/replay e rollback sem truncar estado, regressão P96/P100/B10 e
gates Rust Ubuntu26. Documentar o escopo de política e suas limitações.

Não implementar CA/certificado distinto por endpoint nesta fatia: P100 mantém
uma geração TLS compartilhada. E02 físico é uma campanha separada com prompt
próprio após o aceite de software.

## rev2 — lint de pré-validação

Clippy exigiu condensar a checagem de modo/arquivos compartilhados. Ajustar
somente a forma do predicado e repetir o gate, sem afrouxar a recusa.

## rev3 — replay após restart

O primeiro ensaio P101 confirmou isolamento e negativos de configuração/ACL.
Ampliar o mesmo laboratório para persistir retained em tópico permitido de
publicação no primário e entrega no secundário após reiniciar o mesmo estado.
Isso verifica a política global usada pelo roteador no restore.

## rev4 — contrato de saída do client

O replay chegou, mas o harness procurou `retained` em vez da chave JSON
documentada `retain`; corrigir o oráculo e repetir, sem alterar o broker.
