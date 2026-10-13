# B07/P90 — fuzzing mutacional limitado

Esta campanha usa Rust estável e mutações reais sobre fixtures sintéticas.
Não é um teste LibFuzzer, ASAN ou guiado por cobertura. Aceite e contagens
ficam no [registro P90](../prompts/registros/P90-fuzzing.md), após execução.

## Executar no Ubuntu/WSL

Na raiz do broker, com Rust/Cargo e Python3 já disponíveis:

```sh
python3 scripts/run_fuzz.py --output dist/fuzz/p90.json
```

O driver compila o teste de biblioteca com lockfile preservado e executa
separadamente seis alvos por seed: framing, corpo MQTT, fragmentação e
concatenação, nomes/filtros/matcher, documento/restore, modelo do router.
Seeds padrão: `151195649`, `305419896`, `11400714819323198485`. Para reprodução:

```sh
python3 scripts/run_fuzz.py --seeds 151195649 --targets decode --iterations 25000 --output dist/fuzz/replay.json
```

Os limites são 25000 casos por alvo rápido/seed, 128 documentos/candidatos
por seed e 256 transições de router por seed. O código impõe tetos próprios:
1 milhão de casos rápidos, 1024 documentos, 4096 transições e input65536.
Modificações desses parâmetros no comando não modificam quotas do broker.
Estado é criado em diretórios temporários privados no filesystem Linux.
Nenhuma credencial, serviço ou estado operacional é lido.

## Oráculos e controles

- Framing: avaliação de dígitos RL por pesos de bits, prefixos incompletos,
  teto do pacote completo65536 e comprimento malformado. Não usa encoder.
- Decoder: gramática separada com leitor por fatias, IDs/flags e UTF-8;
  rejeita controles/noncharacters conforme política local, sem normalização.
  ClientID é política adicional da conexão, fora desse oráculo de sintaxe.
- Fragmentação: chunks1..32 e frames concatenados, comparando consumo e
  classificação de bytes ao FrameReader real. O teste é em memória; prazos
  de rede real são ensaios separados, não inferidos por estes resultados.
- Filtros: referência recursiva por níveis com $, `+`, `#`, vazios, unicode,
  tópico1024 bytes; mutação de byte inclui formas UTF-8 inválidas. Ao falhar
  UTF-8, não se tenta construir uma String artificialmente válida.
- Estado: candidatos semânticos inválidos e TOML mutado dentro de WAL válido,
  comparação de validação e restauração. O TOML usa o mesmo desserializador
  da dependência; invariantes semânticos têm referência separada. Isso não
  é um segundo parser TOML independente nem fuzzing de CRC/WAL binário.
- Router: modelo de retained (troca/remoção/quota) e ordem offline QoS1,
  refusas sem atualização parcial, shutdown/reopen e ACK/replay a cada16
  transições. QoS2/ACL/TLS têm outros gates específicos da fase, não são
  inferidos por este modelo open-lab interno.

Cada processo/grupo do teste tem watchdog de120s e teto RSS agregado512MiB.
Somente seu próprio grupo criado em sessão nova é encerrado se exceder limite.
RSS é amostrado a cada20ms: pico informado é amostrado, não medição exata de
alocações instantâneas. O tempo de compilação é separado e limitado a300s.

Corpus está em `tests/fuzz-corpus/` e seeds/contagens/método/hash em JSON sob
`dist/fuzz/` (ignorado). SHA de todas as fontes Rust, manifest/lock, driver e
corpus são comparados antes/depois: edição concorrente impede aceite. Campo
`accepted`: framing conta cabeçalhos completos aceitos (corpo pode faltar),
decoder conta corpos válidos, fragmentação conta streams inteiros válidos,
tópicos conta pares validados, estado conta restore aceito e router conta
transições aceitas. No router `max_input_bytes` é o maior payload observado;
nos alvos byte-oriented é o maior input observado. Falhas síncronas salvam input original/minimizado,
seed e índice; a redução tem no máximo256 tentativas. Falhas assíncronas
guardam seed/índice no log e precisam de reprodução mínima manual antes de
qualquer correção runtime. Não aceitar um alvo só porque os outros passaram.

## Rastreabilidade e limites

[OASIS MQTT3.1.1+Errata01](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/errata01/os/mqtt-v3.1.1-errata01-os-complete.html)
§§1.5.3, 2.2/2.3, 3.1/3.3/3.8/3.10/3.12/3.14 e4.7 fundamentam a sintaxe.
As quotas são política local, não os máximos normativos MQTT. O harness não
muda o comportamento em produção, os formatos, dependências ou licençaMIT.
Dois smoke tests entram na suíte normal; campanhas são explicitamente ignored.
Ausência de crash em campanha finita não prova exaustividade, imunidade a DoS,
energia, hardware físico, desempenho/SLA, conformidade integral ou produção.
