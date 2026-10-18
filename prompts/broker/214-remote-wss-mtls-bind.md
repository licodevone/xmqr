# P214 — WSS mTLS remoto com ativação explícita

Entrada: broker 0.40.0 publicado com WSS mTLS limitado a loopback (P212/P213); client 0.33.0 publicado. C116 perfil local aceito após a tag. Este prompt precede qualquer alteração funcional.

Objetivo: permitir um listener WSS mTLS em endereço não loopback somente com configuração explícita independente, mantendo o comportamento local padrão. Mesmo contexto CA/certificado cliente, usuário/senha, ACL, quota, router, rotação TLS e shutdown do TCP seguro. `Origin` continua recusado; navegador é fase separada.

Escopo: configuração do bind WSS e validação de segurança, documentação e fixture isolada. Não relaxar WS `open-lab`, TCP, credenciais, CA, SAN ou aceitar bind remoto implícito. Valor booleano remoto deve ser estrito, recusar flag isolada e configuração contraditória; nunca registrar segredo. Estado v15 sem migração. Não afirmar que abrir `0.0.0.0` publica serviço sem firewall/rede apropriados.

Aceite: negativos de remoto sem opt-in, opt-in sem bind, modo incorreto, colisão de porta e bind inválido; positivo em rede Docker descartável com client C117 por hostname/SAN remoto, MQTT 3.1.1/5 pub/sub e ACL, retomada do listener local e regressão TCP/TLS; fmt, suíte, Clippy, build, licenças/distribuição e CI da fonte exata. Registrar a entrega como parcial de fase 7. Sem tag/release por este prompt isolado.
