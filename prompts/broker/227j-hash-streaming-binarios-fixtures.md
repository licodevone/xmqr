# P227J v1.0 — hashing de binários em streaming nas fixtures

2026-10-18, antes de alterar código. Pedido da raiz após campanha all6:
69fixtures,65PASS/4FAIL,208.554s; fonte/binários/legados unchanged=true.
Entrada broker0.43.0/HEAD5b01cce; workflow/globalprompt em alteração da raiz,
preservados. Ownership apenas verify_phase6_vbi.py, alias_reason.py e
shared_will.py, novo contrato Python, este prompt e registro próprio.
Nenhum Rust, Cargo, cache de build, distribuição ou arquivo de outro owner.

## Evidência e limites do diagnóstico

Preservar ../.artifacts/p227-acceptance-e-all-6.json, SHA256
2960751664dc5f6619efc02a044f1ab97fedd209654644a5539e73dec0214616.
VBI e aliasReason saíram1/OSError/linha203 da stack, stdout0; sharedWill
também saiu1 sem cenários e com OSError no relatório privado; channelCLI
falhou separadamente em AssertionError de shutdown. Nenhuma dessas quatro
falhas será reescrita ou chamada de PASS retroativo.

OSError e linha de stack não comprovam ENOMEM, errno12 nem causa única.
Houve memória insuficiente em outra operação de build concorrente, mas
isso é correlação, não diagnóstico das fixtures. Identificou-se mecanismo
evitável no código: binary.read_bytes() materializa integralmente o ELF de
128640552bytes antes de sha256; reduzir essa alocação é higiene mensurável,
sem alegar que explica cada falha anterior. Não reproduzir pressão/OOM.

## Mudança mínima autorizada

Adicionar binary_digest(Path) no helper VBI, abrindo rb em context manager
e usando hashlib.file_digest(stream,'sha256').hexdigest(). Alias e sharedWill
importam esse helper e o usam somente para broker_binary_sha256. Hashes dos
pequenos arquivos de script permanecem inalterados em semântica; digest
binário deve manter exatamente o mesmo algoritmo/conteúdo hexadecimal.

Sem mudar cenários, bytes MQTT, controles, ordenação, markers, expectativas,
timeouts, flagsCLI, relatório/cleanup, seleção de filesystem ou resultados
anteriores. Sem fallback que omita hash/erro. Exceção de IO continua falha.
Não corrigir channelCLI nesta frente; raiz/admin investigam separadamente.

## Contratos e validação

Novo scripts/test_phase6_binary_digest.py, unittest/stdlib:

- SHA256 conhecido (vazio/abc) e referência one-shot só para dados sintéticos
  pequenos devem ser idênticos ao streaming; nunca carregar um ELF inteiro.
- Path.read_bytes proibido no contrato, stream guard recusa readall e
  observa readinto com buffer máximo256KiB, garantindo consumo finito.
- Reader privado deve fechar em sucesso e exceçãoIO; erro não vira digest.
- AST dos três pontos broker_binary_sha256 exige chamada ao helper stream;
  importadores devem usar o mesmo helper, não lambda read_bytes para o ELF.

Rodar unittest e três harnesses sequenciais, sem Cargo, em WSL/Python3.14,
estado/temporários nativos/var/tmp, processos/portas privados. Cada execução
usa relatório novo; não remover FAIL nem usar grande experimento de memória.
Primeiro ELF debug congelado fce0b871be72e5cfc7eb5a8dc46d04280075dd21dbbbb5b3677676952c6e9257,
versão0.43.0; depois, se viável, ELF release CI extraído do.deb de mesma
fonte informado pela raiz,1ee611b082b5e8cb14bf881996ce314c391573353cf8971232728cb54a243207,
9303856bytes. Conferir hashes por leitura limitada antes/depois. Não trocar
artefato durante cenário. VBI21,aliasReason9,sharedWill3 mantêm oráculos.

Gates AST/unittest/diff e resultados reais separados no registro. PASS local
não atribui causa ao FAIL anterior nem fecha aceitação global6A–6D, produção,
perda de energia ou interoperabilidade nova. Sem install/serviço/firewall,
segredo/estado real, push/tag/publicação. MIT e licenças preservadas.
