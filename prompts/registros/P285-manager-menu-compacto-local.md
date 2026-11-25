# P285 — menu compacto no Windows local

- PASS: rustfmt do Manager. O artefato local P280 não contém o rótulo longo
  “Iniciar todos os serviços” e contém “Recuperar serviços”.
- PASS: diagnóstico somente leitura do artefato (exit 0): Admin, Broker e
  Client em execução, sem erro de inventário.
- PASS: apenas o processo do Manager foi substituído na sessão interativa 2.
  A cópia em LocalAppData foi conferida por SHA-256 e permaneceu ativa. Os três
  serviços mantiveram exatamente os mesmos estados e PIDs antes/depois.
- BLOCKED: teste, Clippy e build novos não concluídos porque o linker MSVC
  link.exe está ausente (o teste falhou na linkedição, os demais não rodaram).
- NOT RUN: medição visual da largura. Program Files e inicialização do Windows
  inalterados, pois a sessão não tem elevação. Sem publicação.
