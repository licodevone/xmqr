# P227J — hashes binários limitados e novas execuções isoladas

2026-10-18. Promptv1.0 em b087191 precedeu código. Pedido coordenado após
all6, sem Cargo/novo runtime/distribuição nesta frente. Entrada5b01cce,
broker0.43.0; workflow/globalprompt alheios preservados. Skill xmqr-tests
orientou isolamento, evidência e separação entre resultado novo e falha
histórica, sem ampliar autoridade ou prometer aceite total.

## Falhas anteriores preservadas, sem causa inventada

../.artifacts/p227-acceptance-e-all-6.json continua FAIL69fixtures,
65PASS/4FAIL,208.554s. source_unchanged/binaries_unchanged/
legacy_binaries_unchanged=true. SHA256 antes e depois desta contribuição:
2960751664dc5f6619efc02a044f1ab97fedd209654644a5539e73dec0214616.

VBI e aliasReason tiveram exit1/OSError/diagnostic_line203/stdout0,1.048s e
0.881s. SharedWill exit1/stdout0,1.115s no agregado; coordenador também
registrou seu JSON com fixture_error_typeOSError e scenarios vazio. O
channelCLI teve AssertionError de shutdown/linha110,11.85s e é investigado
separadamente pela raiz/admin. Nenhuma dessas quatro linhas foi alterada.

O errno das três falhas não foi registrado pelo agregado; OSError sozinho
não comprova ENOMEM/OS12. Falta de memória observada em outra atividade é
correlação, não prova causal dessas três falhas. Não se fez experimento de
memória/pressão, mediçãoRSS nem tentativa de reproduzirOOM. O achado de
código é concreto: hashing anterior materializava o ELF inteiro em bytes;
o maior insumo tem128640552bytes. A mudança elimina essa alocação integral,
mas PASS posterior isolado não atribui causa ao FAIL agregado anterior.

## Alteração e contratos reais

verify_phase6_vbi.py agora fornece binary_digest(Path): open('rb') em
context manager +hashlib.file_digest(stream,'sha256').hexdigest(). Somente
o ponto broker_binary_sha256 usa essa função. AliasReason e sharedWill
importam o mesmo helper nesse ponto. Algoritmo e SHA continuam idênticos;
hash de scripts pequenos mantém sua semântica anterior. Mudança dos três
scripts:10linhas adicionadas/5removidas. Cenários, MQTT, expectativas,
markers, deadlines, CLI, relatórios e cleanup não mudaram. Nenhuma fonte
Rust, Cargo/lock, serviço, firewall ou dado do operador foi alterado.

Novo scripts/test_phase6_binary_digest.py teve4/4PASS,0.018s,exit0:

- Arquivos mínimos vazio/abc contra SHA256 conhecido independente.
- Path.read_bytes/readall proibidos; stream guard impõe buffer<=256KiB,
  múltiplos readinto e SHA igual à referência one-shot de só4882bytes.
- ErroIO sintético errno5 propaga como erro e reader fecha; não vira hash.
- AST dos três broker_binary_sha256 exige binary_digest(binary), e ambos
  importadores usam o mesmo objeto helper, sem digestELF alternativo.

Comando real, Python3.14/Ubuntu26.04/WSL:

```text
TMPDIR=/var/tmp python3 -B -m unittest discover -s scripts -p test_phase6_binary_digest.py -v
```

AST também fez parsing dos três scripts no contrato; git diff --check PASS.
Sem Cargo ou instalação. Hashes finais dos scripts/teste:

```text
VBI          72d35a2ead597bc9be0d59f6fb70e3d9f6a902dd0d70c50e622e9e48936b831c
aliasReason  cc1007ca49a178647127a2bc59dd6ebb889ca437860f2bbda3a32d58e2100daa
sharedWill   9985ce2adae5e0da99105f94e5ca032bcb7be11b3655c0fe9c8d7c490f011b1e
contratos    78d5fc1aacc43ab4a8122ac515c1180b640b3c56341044a8c36d17ee500e2bfe
```

## Seis execuções reais, sequenciais e sem enfraquecer protocolo

ELFs fornecidos pela raiz, ambos identificados0.43.0. SHA256 conferido por
stream antes/depois, igual ao SHA das cópias privadas de cada relatório:

```text
debug   fce0b871be72e5cfc7eb5a8dc46d04280075dd21dbbbb5b3677676952c6e9257
release 1ee611b082b5e8cb14bf881996ce314c391573353cf8971232728cb54a243207
```

Debug veio de ../.artifacts/p227-binaries/mqtt-broker-p227e-0.43.0;
release9303856bytes veio do.debCI extraído em
../.artifacts/p228-ci-package043/extracted/usr/bin/mqtt-broker. A proveniência
do build/ELF da mesma fonte é fornecida e validada pela raiz; esta frente
não recompilou nem atribui um commit diferente aos artefatos.

Todos os comandos usam TMPDIR=/var/tmp, --state-root /var/tmp,
--label candidate, --broker explícito e --report novo. Os harnesses copiam
ELF para diretório nativo privado, criam estado e portas próprios e eliminam
somente seus recursos. Relatórios nativos preservados em
/var/tmp/xmqr-p227j-reports-6YqNpcCh, sem logs/payloads/chaves/certs/segredos.

| ELF/relatório | Resultado | Tempo observado | SHA256 relatório |
| --- | --- | --- | --- |
|debug-vbi.json|21/21PASS,exit0,cleanupPASS|2.644s|0e36cdfd127d5bf9bd7021e53d01ad8216b323e75b3a02f311c724098253d0c1|
|debug-alias.json|9/9PASS,exit0,cleanupPASS|1.544s|429f014937852f9fe75ee8826dd280a4fe41dc93f82055a6c02eee73129d9b7a|
|debug-shared.json|3/3PASS,exit0,cleanupPASS|3.563s|ef7d1f048907621a6192b313fba44d622597ff89b3ec0c8ec78e7335eb80b5a5|
|release-vbi.json|21/21PASS,exit0,cleanupPASS|1.892s|d407e72ba1b7e308b649aadb7eefc38c01893aa74d82470a564e3ecca617442a|
|release-alias.json|9/9PASS,exit0,cleanupPASS|0.512s|072e65b187a45c959c161d5184ec7e761234acd1272c4f8e5b2730de6b0a5ed5|
|release-shared.json|3/3PASS,exit0,cleanupPASS|2.865s|e34c054f2b205e16d9714c8d668ca873df409d6639a96a347d9ce498e80af69b|

Os três markers finais originais foram emitidos em ambos ELFs:
P227_VBI_PASS, P227_ALIAS_REASON_PASS, P227_SHARED_WILL_PASS. Scripts
conservaram os mesmos21/9/3cenários; não excluíram negativos nem relaxaram
CONNACK/reasons/Will/fairness/3.1.1 para tornar verdes as repetições.

Este resultado não substitui all6, não explica o channelCLI nem promove as
falhas históricas. Aceite integrado/CI/distribuição ficam com a raiz. Sem
alegaçãoTLS/mTLS/powerloss/produção/certificação integral. MIT preservada;
sem push/tag/publicação nesta contribuição.
