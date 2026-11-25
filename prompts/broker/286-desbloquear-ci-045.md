# P286 v1.0 — Desbloquear o aceite do Broker 0.45.0

Entrada: P284 0a9838f. O DEB passou. No Windows, o job 45705127930
parou nos testes do mqtt-admin legado que exigem gravação atômica Unix.
Alinhar a seleção dos testes à plataforma que implementa a operação,
preservando todos no Ubuntu. Parear a CI com o Client corrigido por C160.
Aceite: testes Ubuntu e Windows, SCM, MSI, upgrade e rollback induzido.
Sem alteração de versão, estado persistente ou protocolo.

Revisão v1.1: Ubuntu c2dc94e passou. O MSI parou com WiX WIX7015. Preparar um opt-in explícito na variável de repositório XMQR_WIX7_EULA_ACCEPTED, sem defini-la. O job deve indicar o bloqueio antes de instalar o WiX quando o aceite estiver ausente. Atualizar o pin do Client pareado para 987844a.

Revisão v1.2: CI 45708319493 passou no WiX e no MSI de referência. A criação do MSI Client falhou porque o Git normalizou um manifesto de atribuição fixado por SHA. Preservar os bytes originais nos três arquivos revisados e conferir os blobs staged antes de reexecutar.
