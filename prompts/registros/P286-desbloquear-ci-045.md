# P286 — primeira rodada

- PASS: DEB, upgrade da base publicada, recuperação do binário instalado
  e retorno à 0.43.0 na execução 45705128230.
- FAIL: primeira execução Windows 45705127930 rodou testes de escrita
  atômica Unix no Admin legado. A seleção dos testes foi corrigida e
  o Client foi pareado com a correção C160.

## Rodada com o Client corrigido

- PASS: Ubuntu c2dc94e, CI 45705885484. Rust, Clippy, interop, DEB, upgrade
  0.43.0, rollback Ubuntu e cinco cenários de recuperação aprovados.
- PASS: checksum do DEB arquivado em dist/p286-ubuntu-c2dc94e,
  SHA-256 2167b6467bf09f640da5bc39578aca35b4598cad229e18b302e908328c5ce8fd.
- PASS: testes nativos Windows na execução 45705885540.
- BLOCKED: WiX 7 WIX7015 parou no MSI de referência. O aceite explícito da
  EULA OSMF v1.1 precisa ser autorizado antes da execução. Opt-in preparado
  localmente, sem definir a variável XMQR_WIX7_EULA_ACCEPTED.
- NOT_RUN: MSI do candidato, SCM pareado, upgrade e rollback Windows.
- Client 987844a passou nas execuções 45706979355 e 45706979145.
  Ainda precisa ser testado com o Broker no ensaio integrado de Windows.
