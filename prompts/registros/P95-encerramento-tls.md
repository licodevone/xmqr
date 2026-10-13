# P95 — encerramento TLS e drain de tarefas admitidas

13 de outubro de 2026. Prompt `prompts/broker/95-encerramento-tls.md`,
v1.0 a v1.4, preparados antes das respectivas mutações. Pedido autorizado:
finalizar fase3; correção delimitada pelo coordenador a mqtt/mod.rs,
transport/mod.rs, main.rs e regressões pertinentes. Broker0.11.6 candidato;
client0.9.0 e admin independente0.1.0 não alterados por este incremento.

Ambiente: Windows/WSL Ubuntu26.04, Rust1.99, recursos sintéticos privados,
TMPDIR=/var/tmp, CARGO_BUILD_JOBS=1. /tmp global sem espaço não foi apagado;
nenhum serviço, credencial, firewall, ESP32 ou estado do operador modificado.
AGENTS/contrato/skills Rust, testes e segurança e referências foram lidos.
Fonte inicial af315b5, depois ad7d79b e commits compartilhados e80f979 e
3a5e29d8f09a2bfeba47993a40e16670b4ea2b99 preservados sem reset. Agente não
executou commit/push/tag/release; publicação e snapshots cabem ao coordenador.

## Provas anteriores aos fixes

P91 preservou FAIL da extensão SIGTERM na matriz com Mosquitto, apesar de
59 casos anteriores PASS. Não foi convertido em sucesso ou atribuído ao peer.
Prova TLS direta independente de PythonSSL com suppress_ragged_eofs=False:

- `.artifacts/p91-tls-eof-baseline-1.json` na pasta agrupadora: dois controles
  MQTT DISCONNECT PASS, seis SIGTERM FAIL TLS1.2/TLS1.3, processo exit0 mas
  SSLEOFError/UNEXPECTED_EOF_WHILE_READING. BrokerELF SHA
  d371d2834bc8f0d0f0bbd02ecd76393e4b8a88fb78465f5ed85fa7cad6b88903.
- `.artifacts/p91-tls-eof-baseline-2.json`: dez casos, os dois controles PASS
  e oito SIGTERM FAIL, incluindo handshake parcial aberto; mesmo ELF antigo.
- Regressão Rust actor_error_is_not_masked_by_a_later_connection_drain_timeout
  executou RED exit1 após primeira proposta: erro observado era timeout, mas
  esperado era synthetic actor storage failure. Revisãov1.3 precedeu ajuste
  para timeout_at com deadline absoluto compartilhado; targeted depois GREEN.
- Revisão independente encontrou TLS completo sem primeiro byte MQTT.
  `.artifacts/p91-tls-no-connect-baseline-2.json`: brokerELF intermediário SHA
  69ec47dcd3c74af8f2396b31e0c3e4ad58851b44391894ec6434cd101ca16cf4,
  adminELF f40ecbb5e1641565bbf6ec2cb0e14a7d58973709270bc89c64070ae32b6f9083,
  TLS1.2/TLS1.3 negociados, zeroMQTT, SIGTERM exit0 após3.037/3.026s mas
  2/2FAIL SSLEOFError. Harness SHA
  437c66614807fbfc321ee508df3796f12d0ffa513d7664c9c26516c8ee4c21b7.
  Primeira fixture SAN/hostname errada permanece falha registrada; hostname
  127.0.0.1 correto na prova válida, sem desativar verificação. P95v1.4
  preparado antes de corrigir essa segunda fronteira.

## Alterações e revisão

- mqtt/mod.rs: wrapper de serve_connection tenta shutdown limitado em todos
  os retornos do processamento MQTT, inclusive erro unregister/actor parado,
  preservando erro original. Métrica de conexão engloba o fechamento.
- transport/mod.rs: ConnectionDrain via semáforo de admissão existente,
  RAII inclui preparação/handler/panic; valida representação da capacidade
  antes de Semaphore::new. Sem novos accepts após listener drop. Três tests
  novos de wait por todos permits, panic/drop e cancel sem leak.
- main.rs: stop/drop listener primeiro, barrier actor e drain no mesmo
  deadline total15s, tentar drain mesmo após actorError e priorizar esse erro.
  Três tests de espera, budget total e prioridade mesmo se drain expirar.
- P95v1.4 transport: preparação pós-handshake agrupa resultado; erro de
  certificado ausente/initial-read timeout/I/O/EOF tenta close_notify via
  shutdown_with_deadline3s antes de devolver erro original, sem construir
  sessão MQTT falsa. Handshake TLS que falha não recebe garantia de close.

Não altera CA/SAN/mTLS/ACL, wire MQTT, QoS/WAL, dependências, formato durável,
quotas ou limites4096/65536. Erro de persistência não é ocultado. Fechamento
não leitor permanece limitado. Base normativa conferida:
[RFC8446 seção6.1](https://www.rfc-editor.org/rfc/rfc8446.html#section-6.1),
parafraseada no prompt; sem código/copyleft ou mudança de MIT/notices.

## Gates intermediários realmente executados, antes da revisão v1.4

SHA69ec47dc não é o aceite do novo ELF pós-v1.4. Preservados como evidência:

- cargo fmt --all -- --check:0; clippy --locked --all-targets -- -D warnings:0.
- cargo test --locked -- --test-threads=1:0,135PASS/6ignored. Inclui B06 falhas
  duráveis/sem ACK após storeFail e P80 fechamento não leitor limitado.
- cargo build --locked --release --bins:0; license_inventory.py --check:0.
- P91 strictTLS `.artifacts/p91-tls-eof-candidate-1.json`:10/10PASS, ativo
  SIGTERM≈.032s e handshake parcial realmente admitido≈3.023/3.037s. Harness
  SHA da878f079c8824165e48e087da59dbd05d0c43d7b8982cb207fb006af5716538.
  Esses10 casos não cobriam a borda TLS completo sem CONNECT depois descoberta.
- P90 repetido em dist/fuzz/p95-final.json:18/18PASS, fontes invariantes,
  300000 casos rápidos+384restore+384candidatos semânticos+768router,
  duração32.86s/RSS máximo amostrado10153984bytes. ReportSHA
  5748d2006e519b7472914b467e8473f87d515519e883ec8646b41b64bc227302;
  libtestSHA ac5799136e02739a4dedbdbbf0dda803edd0e85a32faf097fb26e4f7fab7ba19.
- P91wire19 PASS nesse ELF intermediário. Soak interrompido com FAIL em268.599s,
  ready transiente0→1≈.103s e errors0; P91v1.22 ajustou critério quiescente
  após prova e negativos. Não é soak completo/aprovado; ver registro P91.

## Gates finais pós-v1.4

Release0 em1m43s, fmtcheck anterior0, inventário0. ELFbroker final SHA
e57b1e2d26de50d09bb6bdadb74e4c0531dcac15399ece4369f4e0a0824e2987;
ELFadmin legado SHA f40ecbb5e1641565bbf6ec2cb0e14a7d58973709270bc89c64070ae32b6f9083.
Targeted transport6/6PASS exit0 (compile49.72s, tests.04s), incluindo
nonreading/drain/RAII/cancel. Fonte runtime congelada antes dos testes P91,
nenhum novo build substitui esses ELFs durante campanhas.

P91 externo executou e o agente P95 leu os três JSONs:

- `.artifacts/p91-tls-eof-candidate-2.json`:10/10PASS, reportSHA
  415a6a6039b8149241c6a07a950ab9b4fa4b6de09b92a1eb6b14a1e7d45059d1;
  harnessSHA da878f079c8824165e48e087da59dbd05d0c43d7b8982cb207fb006af5716538.
- `.artifacts/p91-tls-no-connect-candidate-1.json`:2/2PASS, TLS1.2/TLS1.3
  negociados, zeroMQTT e EOF limpo, SIGTERM3.023/3.040s e exit0; reportSHA
  118668859ef8a86f13b238d31c5a919aede2b860c6e4eb6bc57fd69ff8487b23;
  harnessSHA 437c66614807fbfc321ee508df3796f12d0ffa513d7664c9c26516c8ee4c21b7.
- `.artifacts/p91-wire-candidate-3.json`:19/19PASS, reportSHA
  f9afa1337a8115fb969931859f2cea74fb014d6a1f199a3d0af113c9f6eafc9b;
  harnessSHA 98fb06b4013df0d4b808eb78baf9aeeb73193cc461f412817b36ddce310774fd.

Todos os reports identificam o mesmo broker e57b1e2d; TLS também o adminf40e.
Portanto RED→GREEN real nas duas fronteiras, sem desligar validação TLS.
SHAs raw das três fontes runtime na cópia Windows compartilhada:
mqtt/mod.rs be0e4b0a538816882202af1c5126eb772a2f8107fbef9abc6637a4b5b23743eb;
transport/mod.rs797745517926d3eb644949bfe8da8da2083cf0412b193daebd6eb9f1a617dd39;
main.rs18310f7c00382fb3df9463eb15a8ac31aefb46e423368725095a8bcf97399aa9.
CRLF/LF de clone podem mudar SHA raw de fonte, não contratos ou termos MIT.

Gates finais executados na fonte congelada, cadeia fail-fast retornou0:

```text
TMPDIR=/var/tmp CARGO_BUILD_JOBS=1
cargo test --locked -- --test-threads=1
cargo clippy --locked --all-targets -- -D warnings
cargo fmt --all -- --check
python3 scripts/run_fuzz.py --iterations 25000 --state-iterations 128 --router-iterations 256 --output dist/fuzz/p95-v14-final.json
```

- FullRust:135PASS/6ignored (campanhas explicitamente repetidas por driver),
  lib113PASS em49s, legacyadmin4PASS em8.30s, main7PASS em.06s,
  integração backup1/adminCLI2/config5/quotas1/version2. B06 falhas I/O,
  commit/ACK/fanout/crash e P80nonreading incluídos e PASS, não presumidos.
- Clippy0 em18.29s, fmtcheck0, inventory0. Buildrelease0 já descrito acima;
  hashes dos ELFs conferidos novamente após gates, inalterados.
- P90 final18/18PASS:300000 casos rápidos+384restore+384 candidatos
  semânticos+768router, 44.1165s, RSS máximo amostrado10211328bytes,
  input65536máx/timeout120s por alvo/RSS512MiB/sample20ms. Fonte invariável
  entre início/fim, sem panic/divergência/limite de tempo/RSS do broker.
  Report dist/fuzz/p95-v14-final.json SHA
  0ee817ed7e1fd282697393184a79c3e4c0977220b6329fbb7ae37ba9cda60bb7;
  libtestSHA144ba7ae840f2178ec8816f8f0278437ba84964dbacf6d63fb27fd57ca071e4a.
  JSON identificou HEADabbe38ca6c041f7328e85054506a4eed22c74c41, dirtytrue
  por registros compartilhados em edição, snapshot SHA das fontes estável.
- git diff --check:0, somente avisos conhecidos LF/CRLF em registros.

P91soak3x600s e matriz externa final são gate separado, em andamento pelo
agente P91 no ELF e57b1e2d. Ainda não aprovados por esses testes curtos.
Coordenador fará clone/artefatos de commit exato; estes gates não equivalem
à validação dos ELFs reconstruídos ou payload de deb/imagens.

## Limitações e aceite

Correção delimitada de teardown, sem conformidade MQTT integral, MQTT5,
produção/SLA, energia, Windows runtime/ARM64/MSRV1.88 exato inferidos.
Deadline pode causar fechamento abrupto de peer deliberadamente não leitor
após o limite, sem pendurar serviço; não prometer close_notify entregue em
rede rompida/fatalTLS. Artefatos locais ignored são evidência local, não
prova pública automática; conservar JSON com releases/commit exato.
Fase3 completa, deb, Docker, GitHub e DockerHub dependem dos gates P91/P92
e publicação pelo coordenador. Nenhum candidato antigo deve ser promovido.
